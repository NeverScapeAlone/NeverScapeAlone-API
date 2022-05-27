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
from api.database.models import OptionsSkill
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


class options_skill(BaseModel):
    """
    Options skill base model containing the types and content expected by the database
    """

    ID: Optional[int]
    user_id: int
    attack: Optional[int]
    hitpoints: Optional[int]
    mining: Optional[int]
    strength: Optional[int]
    agility: Optional[int]
    smithing: Optional[int]
    defence: Optional[int]
    herblore: Optional[int]
    fishing: Optional[int]
    ranged: Optional[int]
    thieving: Optional[int]
    cooking: Optional[int]
    prayer: Optional[int]
    crafting: Optional[int]
    firemaking: Optional[int]
    magic: Optional[int]
    fletching: Optional[int]
    woodcutting: Optional[int]
    runecraft: Optional[int]
    slayer: Optional[int]
    farming: Optional[int]
    construction: Optional[int]
    hunter: Optional[int]


@router.get("/V1/options-skill/", tags=["options", "skill"])
async def get_options_skill(
    login: str,
    token: Optional[int] = None,
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    attack: Optional[int] = Query(0, ge=0, le=1),
    hitpoints: Optional[int] = Query(0, ge=0, le=1),
    mining: Optional[int] = Query(0, ge=0, le=1),
    strength: Optional[int] = Query(0, ge=0, le=1),
    agility: Optional[int] = Query(0, ge=0, le=1),
    smithing: Optional[int] = Query(0, ge=0, le=1),
    defence: Optional[int] = Query(0, ge=0, le=1),
    herblore: Optional[int] = Query(0, ge=0, le=1),
    fishing: Optional[int] = Query(0, ge=0, le=1),
    ranged: Optional[int] = Query(0, ge=0, le=1),
    thieving: Optional[int] = Query(0, ge=0, le=1),
    cooking: Optional[int] = Query(0, ge=0, le=1),
    prayer: Optional[int] = Query(0, ge=0, le=1),
    crafting: Optional[int] = Query(0, ge=0, le=1),
    firemaking: Optional[int] = Query(0, ge=0, le=1),
    magic: Optional[int] = Query(0, ge=0, le=1),
    fletching: Optional[int] = Query(0, ge=0, le=1),
    woodcutting: Optional[int] = Query(0, ge=0, le=1),
    runecraft: Optional[int] = Query(0, ge=0, le=1),
    slayer: Optional[int] = Query(0, ge=0, le=1),
    farming: Optional[int] = Query(0, ge=0, le=1),
    construction: Optional[int] = Query(0, ge=0, le=1),
    hunter: Optional[int] = Query(0, ge=0, le=1),
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    table = OptionsSkill
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if user_id is not None:
        sql = sql.where(table.user_id == user_id)

    if token is not None:
        sql = sql.where(table.token == token)

    if attack is not None:
        sql = sql.where(table.attack == attack)

    if hitpoints is not None:
        sql = sql.where(table.hitpoints == hitpoints)

    if mining is not None:
        sql = sql.where(table.mining == mining)

    if strength is not None:
        sql = sql.where(table.strength == strength)

    if agility is not None:
        sql = sql.where(table.agility == agility)

    if smithing is not None:
        sql = sql.where(table.smithing == smithing)

    if defence is not None:
        sql = sql.where(table.defence == defence)

    if herblore is not None:
        sql = sql.where(table.herblore == herblore)

    if fishing is not None:
        sql = sql.where(table.fishing == fishing)

    if ranged is not None:
        sql = sql.where(table.ranged == ranged)

    if thieving is not None:
        sql = sql.where(table.thieving == thieving)

    if cooking is not None:
        sql = sql.where(table.cooking == cooking)

    if prayer is not None:
        sql = sql.where(table.prayer == prayer)

    if crafting is not None:
        sql = sql.where(table.crafting == crafting)

    if firemaking is not None:
        sql = sql.where(table.firemaking == firemaking)

    if magic is not None:
        sql = sql.where(table.magic == magic)

    if fletching is not None:
        sql = sql.where(table.fletching == fletching)

    if woodcutting is not None:
        sql = sql.where(table.woodcutting == woodcutting)

    if runecraft is not None:
        sql = sql.where(table.runecraft == runecraft)

    if slayer is not None:
        sql = sql.where(table.slayer == slayer)

    if farming is not None:
        sql = sql.where(table.farming == farming)

    if construction is not None:
        sql = sql.where(table.construction == construction)

    if hunter is not None:
        sql = sql.where(table.hunter == hunter)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/options-skill", tags=["options", "skill"])
async def post_options_skill(
    login: str, token: str, options_skill: options_skill
) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    values = options_skill.dict()
    table = options_skill
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
