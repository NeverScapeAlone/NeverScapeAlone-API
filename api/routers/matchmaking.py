import json
import logging
import time
from ast import Delete
from dataclasses import replace
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional
from urllib.request import Request
from xmlrpc.client import Boolean, boolean

import networkx as nx
import numpy as np
import pandas as pd
from api.database.functions import (
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
    verify_user_agent,
    redis_decode,
)
from api.config import redis_client, VERSION
from api.database.models import ActiveMatches, UserQueue, Users, WorldInformation
from api.routers import user_queue
from certifi import where
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi_utils.tasks import repeat_every
from h11 import InformationalResponse
from networkx.algorithms.community import greedy_modularity_communities
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from pyparsing import Opt
from requests import delete, options, request, session
from sqlalchemy import TEXT, TIMESTAMP, select, table, tuple_, values
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case, text
from sqlalchemy.sql.expression import Select, insert, select, update

logger = logging.getLogger(__name__)

router = APIRouter()


class user_active_match(BaseModel):
    user_id: int
    user_queue_ID: int
    party_identifier: str
    activity: str
    party_member_count: int


@router.get("/V1/matchmaking/check-status", tags=["matchmaking"])
async def get_matchmaking_status(
    login: str, discord: str, token: str, user_agent: str | None = Header(default=None)
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(
        login=login, discord=discord, token=token, access_level=0
    )

    key_pattern = f"match:{user_id}:*"
    keys = await redis_client.keys(pattern=key_pattern)
    if not keys:
        return {"detail": "no active matches"}
    return {"detail": "pending matches"}


@router.get("/V1/matchmaking/get-match-information", tags=["matchmaking"])
async def get_matchmaking_status(
    login: str, discord: str, token: str, user_agent: str | None = Header(default=None)
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(
        login=login, discord=discord, token=token, access_level=0
    )

    key_pattern = f"match:{user_id}:*"
    keys = await redis_client.keys(pattern=key_pattern)

    if len(keys) == 0:
        data_array = []
        temp_dict = dict()
        temp_dict["login"] = "NONE"
        temp_dict["discord"] = "NONE"
        temp_dict["verified"] = "NONE"
        temp_dict["runewatch"] = "NONE"
        temp_dict["wdr"] = "NONE"
        temp_dict["party_identifier"] = "NO PARTY"
        temp_dict["has_accepted"] = False
        temp_dict["timestamp"] = str(int(time.time()))
        temp_dict["discord_invite"] = "NONE"
        temp_dict["version"] = VERSION
        data_array.append(temp_dict)
        return data_array

    key_chain = []
    for key in keys:
        key = str(key)
        party_ID = "*" + key[key.find("PARTY=") :][:-1]
        sub_keys = await redis_client.keys(pattern=party_ID)
        key_chain += sub_keys

    byte_data = await redis_client.mget(keys=key_chain)
    match_data = await redis_decode(bytes_encoded=byte_data)
    df_match = pd.DataFrame(match_data)

    user_ids = df_match.user_id.values
    ids = [f"user:{user_id}" for user_id in user_ids]
    byte_data = await redis_client.mget(keys=ids)
    user_data = await redis_decode(bytes_encoded=byte_data)
    df_user = pd.DataFrame(user_data)

    df = pd.merge(df_user, df_match, how="inner", right_on="user_id", left_on="user_id")

    cleaned_data = []
    for index, row in df.iterrows():
        temp_dict = dict()
        temp_dict["login"] = row.login
        temp_dict["discord"] = "NONE" if row.discord is None else str(row.discord)
        temp_dict["verified"] = row.verified
        temp_dict["runewatch"] = "NONE" if row.runewatch is None else str(row.runewatch)
        temp_dict["wdr"] = "NONE" if row.wdr is None else str(row.wdr)
        temp_dict["party_identifier"] = row.party_identifier
        temp_dict["has_accepted"] = row.has_accepted
        temp_dict["timestamp"] = str(int(time.time()))
        temp_dict["discord_invite"] = (
            "NONE" if row.discord_invite is None else str(row.discord_invite)
        )
        temp_dict["version"] = VERSION
        cleaned_data.append(temp_dict)

    data = cleaned_data

    if len(data) <= 1:
        data_array = []
        temp_dict = dict()
        temp_dict["login"] = "NONE"
        temp_dict["discord"] = "NONE"
        temp_dict["verified"] = "NONE"
        temp_dict["runewatch"] = "NONE"
        temp_dict["wdr"] = "NONE"
        temp_dict["party_identifier"] = "NO PARTY"
        temp_dict["has_accepted"] = False
        temp_dict["timestamp"] = str(int(time.time()))
        temp_dict["discord_invite"] = "NONE"
        temp_dict["version"] = VERSION
        data_array.append(temp_dict)
        return data_array

    return data


@router.get("/V1/matchmaking/accept", tags=["matchmaking"])
async def get_accept_matchmaking_request(
    login: str,
    discord: str,
    token: str,
    activity: str,
    user_agent: str | None = Header(default=None),
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(
        login=login, discord=discord, token=token, access_level=0
    )
    key = f"match:{user_id}*"
    matches = await redis_client.keys(key)

    remove_queue = []
    remove_matches = []
    for match in matches:
        if str(match).find(f"PARTY={activity}$") == -1:
            match = match.decode("utf-8")
            start = match.find("PARTY=")
            shift = len("PARTY=")
            end = match.find("$")
            event = match[start + shift : end]
            remove_queue.append(event)
            remove_matches.append(match)
        else:
            byte_data = await redis_client.get(name=match)
            data = await redis_decode(bytes_encoded=byte_data)
            data[0]["has_accepted"] = True
            data = str(data[0])
            await redis_client.set(name=match, value=data)

    remove_queue = [f"queue:{user_id}:{queue}" for queue in remove_queue]
    remove_matches = [match for match in remove_matches]
    delete_keys = remove_queue + remove_matches
    if delete_keys:
        await redis_client.delete(*delete_keys)

    return {"detail": "match accepted"}


@router.get("/V1/matchmaking/deny", tags=["matchmaking"])
async def get_deny_matchmaking_request(
    login: str, discord: str, token: str, user_agent: str | None = Header(default=None)
) -> json:
    """passes request to user_queue get user queue cancel, which will remove active match and queue. Causing reset. Can be reconfigured later if needed."""
    await user_queue.get_user_queue_cancel(
        login=login, discord=discord, token=token, user_agent=user_agent
    )
    return {"detail": "queue canceled"}


@router.get("/V1/matchmaking/end-session", tags=["matchmaking"])
async def get_end_session_matchmaking_request(
    login: str, discord: str, token: str, user_agent: str | None = Header(default=None)
) -> json:
    """passes request to user_queue get user queue cancel, which will remove active match and queue. Causing reset. Can be reconfigured later if needed."""
    await user_queue.get_user_queue_cancel(
        login=login,
        discord=discord,
        token=token,
        route_type="end session",
        user_agent=user_agent,
    )
    return {"detail": "match ended"}
