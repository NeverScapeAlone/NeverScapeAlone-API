from ast import Delete
import json
from cgitb import text
from dataclasses import replace
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
import queue
from typing import Optional
import time
from urllib.request import Request
from xmlrpc.client import Boolean, boolean
from certifi import where

from pymysql import Timestamp

from api.database.functions import (
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
    verify_user_agent,
)
from api.database.models import UserQueue
from fastapi import APIRouter, Header, HTTPException, Query, status
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pyparsing import Opt
from requests import delete, options, request
from sqlalchemy import TEXT, TIMESTAMP, select, values
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, insert, select, update

router = APIRouter()


class sub_payload(BaseModel):
    """inner layer for content"""

    party_member_count: int
    self_experience_level: int
    partner_experience_level: int
    us_east: bool
    us_west: bool
    eu_central: bool
    eu_west: bool
    oceania: bool
    f2p: bool
    p2p: bool


class content(BaseModel):
    """Wrapper configuration for sub_payload"""

    activity: str
    configuration: sub_payload


class queue_post(BaseModel):
    """Wrapper for content"""

    Payload: list[content]


class input_values(BaseModel):
    """flattened model for queue start"""

    user_id: int
    in_queue: bool
    activity: str
    party_member_count: int
    self_experience_level: int
    partner_experience_level: int
    us_east: bool
    us_west: bool
    eu_central: bool
    eu_west: bool
    oceania: bool
    f2p: bool
    p2p: bool


@router.get("/V1/queue/pool", tags=["matchmaking"])
async def get_queue_pool(
    # User Items
    login: str = Query(..., min_length=1, max_length=12),
    token: str = Query(..., min_length=32, max_length=32),
    user_agent: str | None = Header(default=None),
    # Table items
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    in_queue: Optional[bool] = Query(False),
    activity: Optional[str] = None,
    party_member_count: Optional[int] = None,
    self_experience_level: Optional[int] = None,
    partner_experience_level: Optional[int] = None,
    us_east: Optional[bool] = Query(False),
    us_west: Optional[bool] = Query(False),
    eu_central: Optional[bool] = Query(False),
    eu_west: Optional[bool] = Query(False),
    oceania: Optional[bool] = Query(False),
    f2p: Optional[bool] = Query(False),
    p2p: Optional[bool] = Query(False),
    # row get items
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
):

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/queue/start", tags=["matchmaking"])
async def post_user_queue_start(
    user_options: queue_post,
    login: str = Query(..., min_length=1, max_length=12),
    token: str = Query(..., min_length=32, max_length=32),
    user_agent: str | None = Header(default=None),
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(login=login, token=token, access_level=0)

    incoming_content = user_options.Payload
    values = []
    for activities in incoming_content:
        value = input_values(
            user_id=user_id,
            in_queue=True,
            activity=activities.activity,
            party_member_count=activities.configuration.party_member_count,
            self_experience_level=activities.configuration.self_experience_level,
            partner_experience_level=activities.configuration.partner_experience_level,
            us_east=activities.configuration.us_east,
            us_west=activities.configuration.us_west,
            eu_central=activities.configuration.eu_central,
            eu_west=activities.configuration.eu_west,
            oceania=activities.configuration.oceania,
            f2p=activities.configuration.f2p,
            p2p=activities.configuration.p2p,
        )
        values.append(value.dict())

    table = UserQueue
    sql = insert(table).values(values).prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)

    return {"detail": "queue started"}


@router.get("/V1/queue/cancel", tags=["matchmaking"])
async def get_user_queue_cancel(
    login: str = Query(..., min_length=1, max_length=12),
    token: str = Query(..., min_length=32, max_length=32),
    user_agent: str | None = Header(default=None),
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(login=login, token=token, access_level=0)
    table = UserQueue

    sql = update(table).where(table.user_id == user_id).values(in_queue=False)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)

    return {"detail": "queue canceled"}
