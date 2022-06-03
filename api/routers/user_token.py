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
from sqlalchemy.sql.expression import Select, select, insert

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


@router.get("/V1/user-token/", tags=["user", "token"])
async def get_user_token(
    login: str,
    ID: Optional[int] = None,
    user_id: int = None,
    auth_level: Optional[int] = None,
    token: Optional[str] = None,
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:
    """
    Args:\n
        ID (Optional[int]): ID of entry\n
        user_id (int): user id of token\n
        auth_level (Optional[int]): auth level, 0 - normal user, 9 - highest user (administrator)\n
        token (Optional[int]): token\n
        row_count (Optional[int], optional): _description_. Defaults to Query(100, ge=1, le=1000).\n
        page (Optional[int], optional): _description_. Defaults to Query(1, ge=1).\n

    Returns:\n
        json: requested output\n
    """

    if not await verify_token(login=login, token=token, access_level=9):
        return

    table = UserToken
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if user_id is not None:
        sql = sql.where(table.user_id == user_id)

    if auth_level is not None:
        sql = sql.where(table.auth_level == auth_level)

    if token is not None:
        sql = sql.where(table.token == token)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/user-token", tags=["user", "token"])
async def post_user_token(login: str, token: str, user_token: user_token) -> json:
    """
    Args:\n
        user_token (user_token): user token model\n

    Returns:\n
        json: {"ok": "ok"}\n
    """

    if not await verify_token(login=login, token=token, access_level=9):
        return

    values = user_token.dict()
    table = UserToken
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}


@router.post("/V1/user-token/register", tags=["user", "token"])
async def register_user_token(
    register_account: register_account, user_agent: str | None = Header(default=None)
) -> json:

    if not await is_valid_rsn(login=register_account.login):
        return

    # if not await verify_user_agent(user_agent=user_agent):
    #     return

    login = register_account.login
    token = register_account.token

    table = Users
    sql = insert(table).values({"login": login})
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data_post = await session.execute(sql)

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
