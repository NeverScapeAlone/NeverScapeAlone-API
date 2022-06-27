from cgitb import text
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
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
)
from api.database.models import UserPoints, UserToken
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from sqlalchemy import BIGINT, DATETIME, TIMESTAMP, VARCHAR, BigInteger, func, select
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, select, insert

router = APIRouter()


class user_points(BaseModel):
    """
    User Points base model containing the types and content expected by the database
    """

    ID: Optional[int]
    user_id: int
    points: int


@router.get("/V1/user-points/", tags=["user"])
async def get_user_points(
    login: str,
    discord: str,
    token: Optional[int] = None,
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    points: Optional[int] = None,
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:
    """
    Args:\n
        ID (Optional[int]): ID of entry\n
        user_id (int): user id of token\n
        token (Optional[int]): token\n
        row_count (Optional[int], optional): _description_. Defaults to Query(100, ge=1, le=1000).\n
        page (Optional[int], optional): _description_. Defaults to Query(1, ge=1).\n

    Returns:\n
        json: requested output\n
    """

    if not await verify_token(
        login=login, discord=discord, token=token, access_level=9
    ):
        return

    table = UserPoints
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if user_id is not None:
        sql = sql.where(table.user_id == user_id)

    if points is not None:
        sql = sql.where(table.points == points)

    if token is not None:
        sql = sql.where(table.token == token)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/user-points", tags=["user"])
async def post_user_token(
    login: str, discord: str, token: str, user_points: user_points
) -> json:
    """
    Args:\n
        user_points (user_points): user points model\n

    Returns:\n
        json: {"ok": "ok"}\n
    """

    if not await verify_token(
        login=login, discord=discord, token=token, access_level=9
    ):
        return

    values = user_points.dict()
    table = UserPoints
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
