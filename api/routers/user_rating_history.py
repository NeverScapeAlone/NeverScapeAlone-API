import json
from datetime import datetime
from pickletools import optimize
from typing import Optional
from urllib.request import Request

from api.database.functions import (
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
)
from api.database.models import UserRatingHistory
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


class user_rating_history(BaseModel):
    """
    User Rating History base model containing the types and content expected by the database
    """

    ID: Optional[int]
    timestamp: Optional[datetime]
    s_user_id: Optional[int]
    r_user_id: Optional[int]
    rating: Optional[int]
    comment: Optional[str]
    request_history_id: Optional[int]


@router.get("/V1/user-rating-history/", tags=["user"])
async def get_user_rating_history(
    token: str,
    login: str,
    ID: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    s_user_id: Optional[int] = None,
    r_user_id: Optional[int] = None,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
    request_history_id: Optional[int] = None,
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:
    """
    Args:\n
        token (str): token of the user accessing this content\n
        ID (Optional[int]): ID of the entry\n
        timestamp (Optional[datetime]): timestamp of the entry\n
        s_user_id (Optional[int]): sending user ID\n
        r_user_id (Optional[int]): receiving user ID\n
        rating (Optional[int]): rating that the sending user is giving the receiving user\n
        comment (Optional[str]): comment left by the sending user to the rating user\n
        request_history_id (Optional[int]): request history ID relevant to the rating given\n
        row_count (Optional[int], optional): row counts to be pulled for the relevant GET request. Defaults to Query(100, ge=1, le=1000).\n
        page (Optional[int], optional): page to be pulled for the relevant GET request. Defaults to Query(1, ge=1).\n

    Returns:\n
        json: JSON response object of the above content\n
    """

    table = UserRatingHistory
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if timestamp is not None:
        sql = sql.where(table.timestamp == timestamp)

    if s_user_id is not None:
        sql = sql.where(table.s_user_id == s_user_id)

    if r_user_id is not None:
        sql = sql.where(table.r_user_id == r_user_id)

    if rating is not None:
        sql = sql.where(table.rating == rating)

    if comment is not None:
        sql = sql.where(table.comment == comment)

    if request_history_id is not None:
        sql = sql.where(table.request_history_id == request_history_id)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/user-rating-history", tags=["user"])
async def post_user_rating_history(
    login: str, token: str, user_rating_history: user_rating_history
) -> json:
    """
    Args:\n
        user_rating_history (user_rating_history): User rating history model\n
    Returns:\n
        json: {"ok": "ok"}\n
    """

    values = user_rating_history.dict()
    table = UserRatingHistory
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
