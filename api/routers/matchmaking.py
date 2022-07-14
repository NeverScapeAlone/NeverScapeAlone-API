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

    table = ActiveMatches
    sql = select(table).where(table.user_id == user_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    if len(sqlalchemy_result(data).rows2dict()) == 0:
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

    table = ActiveMatches
    sql_user_actives = select(table).where(table.user_id == user_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql_user_actives)

    data = sqlalchemy_result(data).rows2dict()
    if len(data) == 0:
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

    df = pd.DataFrame(data)
    party_identifiers = df.party_identifier.unique()

    sql: Select = select(
        columns=[
            Users.login,
            Users.discord,
            Users.verified,
            Users.runewatch,
            Users.wdr,
            ActiveMatches.party_identifier,
            ActiveMatches.has_accepted,
            ActiveMatches.timestamp,
            ActiveMatches.discord_invite,
        ]
    )

    sql = sql.join(Users, ActiveMatches.user_id == Users.user_id)
    sql = sql.where(ActiveMatches.party_identifier.in_(party_identifiers))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    cleaned_data = []
    for c, d in enumerate(data):
        temp_dict = dict()
        temp_dict["login"] = d[0]
        temp_dict["discord"] = "NONE" if d[1] is None else str(d[1])
        temp_dict["verified"] = d[2]
        temp_dict["runewatch"] = "NONE" if d[3] is None else str(d[3])
        temp_dict["wdr"] = "NONE" if d[4] is None else str(d[4])
        temp_dict["party_identifier"] = d[5]
        temp_dict["has_accepted"] = d[6]
        temp_dict["timestamp"] = str(int(time.mktime(d[7].timetuple())))
        temp_dict["discord_invite"] = "NONE" if d[8] is None else str(d[8])
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
    login: str, discord: str, token: str, user_agent: str | None = Header(default=None)
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(
        login=login, discord=discord, token=token, access_level=0
    )

    user_id = str(int(user_id))

    statement = f"""
    UPDATE active_matches as am2
    SET am2.has_accepted = 1
    WHERE am2.ID = (
        SELECT * FROM
            (
            SELECT
                am1.ID
            FROM active_matches as am1
            WHERE 1=1
                and am1.user_id = {str(user_id)}
            ORDER BY am1.ID desc
            LIMIT 1
            ) 
        as t);

    UPDATE active_matches as am2
    SET am2.has_accepted = 2
    WHERE am2.ID in (
        SELECT * FROM
    (
        SELECT
            am1.ID
        FROM active_matches as am1
        WHERE 1=1
            and am1.user_id = {str(user_id)}
            and am1.has_accepted = 0
        ORDER BY am1.ID desc
    ) as t);
    
    UPDATE user_queue as uq
    SET uq.in_queue = 0
    WHERE uq.ID in (
        SELECT * FROM
    (
        SELECT
            am.user_queue_ID
        FROM active_matches as am
        WHERE 1=1
            and am.user_id = {str(user_id)}
            and am.has_accepted = 2
        ORDER BY am.ID desc
    ) as t);

    """

    sql = text(statement)
    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)
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
