from atexit import register
from cgitb import text
from collections import UserDict
from datetime import datetime
import json
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional
from urllib.request import Request
from h11 import InformationalResponse

from pyparsing import Opt
from requests import request

from api.database.functions import (
    is_valid_rsn,
    verify_user_agent,
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    validate_discord,
    verify_token,
)
from api.database.models import UserToken, Users
from fastapi import APIRouter, HTTPException, Query, status, Header
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from sqlalchemy import BIGINT, DATETIME, TIMESTAMP, VARCHAR, BigInteger, func, select
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, select, insert, update

router = APIRouter()


class user_token(BaseModel):
    """
    User Token base model containing the types and content expected by the database
    """

    user_id: int
    token: str


class register_account(BaseModel):
    login: str
    token: str
    discord: str


@router.post("/V1/user-token/register", tags=["user"])
async def register_user_token(
    register_account: register_account, user_agent: str | None = Header(default=None)
) -> json:

    login = register_account.login
    token = register_account.token
    discord = register_account.discord

    if not await is_valid_rsn(login=login):
        return
    if not await verify_user_agent(user_agent=user_agent):
        return

    discord = await validate_discord(discord=discord)

    table = Users
    sql = insert(table).values({"login": login, "discord": discord})
    sql = sql.prefix_with("ignore")

    sql_update = update(table).where(table.login == login).values(discord=discord)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)
            await session.execute(sql_update)

    sql: Select = select(table).where(table.login == login)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data_get = await session.execute(sql)

    data = sqlalchemy_result(data_get).rows2dict()

    if len(data) == 0:
        raise HTTPException(
            202,
            detail="registration failure",
        )

    user_id = data[0]["user_id"]

    table = UserToken
    values = {"token": token, "user_id": user_id}
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"detail": "registered"}
