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
from requests import delete, options, request, session
from sqlalchemy import TEXT, TIMESTAMP, select, table, tuple_, values
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, insert, select, update

router = APIRouter()


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
    keys = await redis_client.keys("match:False*")

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
        raise HTTPException(
            status_code=202,
            detail=f"no information",
        )
        return

    data = await redis_client.mget(keys=keys)
    cleaned = await redis_decode(bytes_encoded=data)
    for match in cleaned:
        m = models.match.parse_obj(match)
        if not m.discord_invite:
            print(m)
    return


@router.post("/V1/discord/post-invites", tags=["discord"])
async def post_invites(token: str, request: Request) -> json:
    if token != config.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return
    # TODO fix post-invites

    invite_pairs = await request.json()
    values = json.loads(invite_pairs)["invite_pairs"]
    statements = []
    for value in values:
        party = value["party_identifier"]
        invite = value["discord_invite"]
        sql = f"""update active_matches set discord_invite = "{invite}" where party_identifier = "{party}";"""
        statements.append(sql)
    all_statements = " ".join(statements)

    if len(all_statements) == 0:
        return

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(all_statements)
