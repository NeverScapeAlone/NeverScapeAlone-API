import json
import os
from cgitb import text
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional

import api.config as config
from api.config import redis_client
import pandas as pd
from api.database.functions import (
    USERDATA_ENGINE,
    is_valid_rsn,
    sqlalchemy_result,
    get_match_from_ID,
    validate_discord,
    redis_decode,
)
import logging
from api.database.models import ActiveMatches, UserQueue, Users, WorldInformation
import api.database.models as models
from certifi import where
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi_utils.tasks import repeat_every
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from pyparsing import Opt
from requests import Response, delete, options, request, session
from sqlalchemy import TEXT, TIMESTAMP, select, table, tuple_, values
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, insert, select, update

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/V1/discord/verify", tags=["discord"])
async def verify_discord_account(login: str, discord_id: str, token: str) -> json:

    if not await is_valid_rsn(login=login):
        return

    if token != config.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return

    table = Users
    sql = select(table)
    sql = sql.where(table.login == login)
    sql = sql.where(table.discord_id == discord_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data).rows2dict()

    if len(data) == 0:
        raise HTTPException(
            status_code=202,
            detail=f"no information",
        )
        return

    if len(data) > 1:
        raise HTTPException(
            status_code=202,
            detail=f"contact support",
        )
        return

    if len(data) == 1:
        if data[0]["verified"] == True:
            raise HTTPException(
                status_code=200,
                detail=f"already verified",
            )
            return

        table = Users
        sql = update(table)
        sql = sql.where(table.login == login)
        sql = sql.where(table.discord_id == discord_id)
        sql = sql.values(verified=True)

        async with USERDATA_ENGINE.get_session() as session:
            session: AsyncSession = session
            async with session.begin():
                await session.execute(sql)

        raise HTTPException(
            status_code=200,
            detail=f"verified",
        )
    return


@router.get("/V1/discord/get-active-queues", tags=["discord"])
async def get_active_queues(token: str) -> json:
    if token != config.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return
    keys = await redis_client.keys("match:*False")
    if not keys:
        raise HTTPException(
            status_code=202,
            detail=f"no information",
        )
        return

    d = dict()
    for key in keys:
        key = key.decode("utf-8")
        activity = key[key.find("ACTIVITY") + len("ACTIVITY=") : key.find(":PRIVATE")]
        if activity in list(d.items()):
            d[activity] += 1
        else:
            d[activity] = 1

    response = json.dumps(d)
    response = json.loads(response)
    return response


@router.get("/V1/discord/get-active-matches", tags=["discord"])
async def get_active_matches(token: str) -> json:
    if token != config.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return

    keys = await redis_client.keys("match:*")
    if not keys:
        return {"active_matches_discord": None}

    data = await redis_client.mget(keys=keys)
    cleaned = await redis_decode(bytes_encoded=data)

    active_matches_discord = []
    for match in cleaned:
        m = models.match.parse_obj(match)
        if not m.discord_invite:
            am = models.active_match_discord.parse_obj(m.dict())
            am.player_count = len(m.players)
            active_matches_discord.append(am.dict())

    response = {"active_matches_discord": active_matches_discord}
    response = json.dumps(response)
    response = json.loads(response)
    return response


@router.post("/V1/discord/post-invites", tags=["discord"])
async def post_invites(token: str, request: Request) -> json:
    if token != config.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return
    j = await request.json()
    j = json.loads(j)
    payload = j["invites"]
    for match in payload:
        am = models.active_match_discord.parse_obj(match)
        key, m = await get_match_from_ID(group_identifier=am.ID)
        m.discord_invite = am.discord_invite
        await redis_client.set(name=key, value=str(m.dict()))
        logger.info(f"Invite {am.discord_invite} created for {am.ID}")
