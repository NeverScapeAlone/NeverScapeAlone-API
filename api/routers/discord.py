import json
import os
from cgitb import text
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional

import api.config as config
from api.database.functions import (
    USERDATA_ENGINE,
    is_valid_rsn,
    sqlalchemy_result,
    validate_discord,
)
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
from sqlalchemy.sql.expression import Select, insert, select, update

router = APIRouter()


@router.get("/V1/discord/verify", tags=["discord"])
async def verify_discord_account(login: str, discord: str, token: str) -> json:

    if not await is_valid_rsn(login=login):
        return

    discord = await validate_discord(discord=discord)

    if token != config.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return

    table = Users
    sql = select(table)
    sql = sql.where(table.login == login)
    sql = sql.where(table.discord == discord)

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
        sql = sql.where(table.discord == discord)
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
