import json
from cgitb import text
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional
from urllib.request import Request

from api.database.functions import (
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
)
from api.database.models import Users
from fastapi import APIRouter, HTTPException, Query, status
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from pyparsing import Opt
from requests import request
from sqlalchemy import BIGINT, DATETIME, TIMESTAMP, VARCHAR, BigInteger, func, select
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, insert, select

router = APIRouter()


class users(BaseModel):
    """
    Users base model containing the types and content expected by the database
    """

    user_id: Optional[int]
    login: Optional[str]
    timestamp: Optional[datetime]


@router.get("/V1/users/", tags=["user"])
async def get_users(
    token: str,
    user_id: Optional[int] = None,
    login: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    self_lookup: Optional[bool] = True,
    row_count: Optional[int] = 100,
    page: Optional[int] = 1,
) -> json:
    """
    Args:\n
        token (str): token of the authorized user\n
        user_id (Optional[int], optional): user id. Defaults to None.\n
        login (Optional[str], optional): login username. Defaults to None.\n
        password (Optional[str], optional): hashed/salted password to be checked against on login. Defaults to None.\n
        timestamp (Optional[datetime], optional): timestamp of creation. Defaults to None.\n
        self_lookup (Optional[bool]), optional: toggles if the get request is for a self-lookup
        row_count (Optional[int], optional): row count to be chosen at time of get. Defaults to Query(100, ge=1, le=1000).\n
        page (Optional[int], optional): page selection. Defaults to Query(1, ge=1).\n

    Returns:\n
        json: output as listed above\n
    """

    if not await verify_token(login=login, token=token, access_level=9):
        return

    table = Users
    sql: Select = select(table)

    if not self_lookup:
        if user_id is not None:
            sql = sql.where(table.user_id == user_id)
        if timestamp is not None:
            sql = sql.where(table.timestamp == timestamp)
    if login is not None:
        sql = sql.where(table.login == login)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/users", tags=["user"])
async def post_users(login: str, token: str, users: users) -> json:
    """
    Args:\n
        users (users): users model\n
        login (str): user's login username
        token (str): user's token information

    Returns:\n
        json: {"ok": "ok"}\n
    """

    if not await verify_token(login=login, token=token, access_level=9):
        return

    values = users.dict()
    table = Users
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
