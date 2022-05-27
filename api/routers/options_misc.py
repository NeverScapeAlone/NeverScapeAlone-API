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
from requests import options, request

from api.database.functions import (
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
)
from api.database.models import OptionsMisc
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


class options_misc(BaseModel):
    """
    Options misc base model containing the types and content expected by the database
    """

    ID: Optional[int]
    user_id: int
    pvp_mage_bank: Optional[int]
    pvp_deep_wild: Optional[int]
    pvp_one_iteming: Optional[int]
    pvp_multi: Optional[int]
    pvp_singles: Optional[int]
    pvp_rev_caves: Optional[int]
    relaxing: Optional[int]
    questing: Optional[int]
    exploring: Optional[int]
    looking_for_mentor: Optional[int]
    looking_for_mentee: Optional[int]
    falador_party_room: Optional[int]


@router.get("/V1/options-misc/", tags=["options", "misc"])
async def get_options_misc(
    login: str,
    token: Optional[int] = None,
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    pvp_mage_bank: Optional[int] = Query(0, ge=0, le=1),
    pvp_deep_wild: Optional[int] = Query(0, ge=0, le=1),
    pvp_one_iteming: Optional[int] = Query(0, ge=0, le=1),
    pvp_multi: Optional[int] = Query(0, ge=0, le=1),
    pvp_singles: Optional[int] = Query(0, ge=0, le=1),
    pvp_rev_caves: Optional[int] = Query(0, ge=0, le=1),
    relaxing: Optional[int] = Query(0, ge=0, le=1),
    questing: Optional[int] = Query(0, ge=0, le=1),
    exploring: Optional[int] = Query(0, ge=0, le=1),
    looking_for_mentor: Optional[int] = Query(0, ge=0, le=1),
    looking_for_mentee: Optional[int] = Query(0, ge=0, le=1),
    falador_party_room: Optional[int] = Query(0, ge=0, le=1),
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    table = OptionsMisc
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if user_id is not None:
        sql = sql.where(table.user_id == user_id)

    if token is not None:
        sql = sql.where(table.token == token)

    if pvp_mage_bank is not None:
        sql = sql.where(table.pvp_mage_bank == pvp_mage_bank)

    if pvp_deep_wild is not None:
        sql = sql.where(table.pvp_deep_wild == pvp_deep_wild)

    if pvp_one_iteming is not None:
        sql = sql.where(table.pvp_one_iteming == pvp_one_iteming)

    if pvp_multi is not None:
        sql = sql.where(table.pvp_multi == pvp_multi)

    if pvp_singles is not None:
        sql = sql.where(table.pvp_singles == pvp_singles)

    if pvp_rev_caves is not None:
        sql = sql.where(table.pvp_rev_caves == pvp_rev_caves)

    if relaxing is not None:
        sql = sql.where(table.relaxing == relaxing)

    if questing is not None:
        sql = sql.where(table.questing == questing)

    if exploring is not None:
        sql = sql.where(table.exploring == exploring)

    if looking_for_mentor is not None:
        sql = sql.where(table.looking_for_mentor == looking_for_mentor)

    if looking_for_mentee is not None:
        sql = sql.where(table.looking_for_mentee == looking_for_mentee)

    if falador_party_room is not None:
        sql = sql.where(table.falador_party_room == falador_party_room)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/options-misc", tags=["options", "misc"])
async def post_options_misc(login: str, token: str, options_misc: options_misc) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    values = options_misc.dict()
    table = options_misc
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
