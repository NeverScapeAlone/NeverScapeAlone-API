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
from api.database.models import OptionsBoss
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


class options_boss(BaseModel):
    """
    Options boss base model containing the types and content expected by the database
    """

    ID: Optional[int]
    user_id: int
    abyssal_sire: Optional[int]
    alchemical_hydra: Optional[int]
    barrows_chests: Optional[int]
    bryophyta: Optional[int]
    callisto: Optional[int]
    cerberus: Optional[int]
    chambers_of_xeric: Optional[int]
    chambers_of_xeric_challenge_mode: Optional[int]
    chaos_elemental: Optional[int]
    chaos_fanatic: Optional[int]
    commander_zilyana: Optional[int]
    corporeal_beast: Optional[int]
    dagannoth_prime: Optional[int]
    dagannoth_rex: Optional[int]
    dagannoth_supreme: Optional[int]
    crazy_archaeologist: Optional[int]
    deranged_archaeologist: Optional[int]
    general_graardor: Optional[int]
    giant_mole: Optional[int]
    grotesque_guardians: Optional[int]
    hespori: Optional[int]
    kalphite_queen: Optional[int]
    king_black_dragon: Optional[int]
    kraken: Optional[int]
    kreearra: Optional[int]
    kril_tsutsaroth: Optional[int]
    mimic: Optional[int]
    nex: Optional[int]
    nightmare: Optional[int]
    phosanis_nightmare: Optional[int]
    obor: Optional[int]
    sarachnis: Optional[int]
    scorpia: Optional[int]
    skotizo: Optional[int]
    tempoross: Optional[int]
    the_gauntlet: Optional[int]
    the_corrupted_gauntlet: Optional[int]
    theatre_of_blood: Optional[int]
    theatre_of_blood_hard_mode: Optional[int]
    thermonuclear_smoke_devil: Optional[int]
    tzkal_zuk: Optional[int]
    tztok_jad: Optional[int]
    venenatis: Optional[int]
    vetion: Optional[int]
    vorkath: Optional[int]
    wintertodt: Optional[int]
    zalcano: Optional[int]
    zulrah: Optional[int]


@router.get("/V1/options-boss/", tags=["options", "boss"])
async def get_options_boss(
    login: str,
    token: Optional[int] = None,
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    abyssal_sire: Optional[int] = Query(0, ge=0, le=1),
    alchemical_hydra: Optional[int] = Query(0, ge=0, le=1),
    barrows_chests: Optional[int] = Query(0, ge=0, le=1),
    bryophyta: Optional[int] = Query(0, ge=0, le=1),
    callisto: Optional[int] = Query(0, ge=0, le=1),
    cerberus: Optional[int] = Query(0, ge=0, le=1),
    chambers_of_xeric: Optional[int] = Query(0, ge=0, le=1),
    chambers_of_xeric_challenge_mode: Optional[int] = Query(0, ge=0, le=1),
    chaos_elemental: Optional[int] = Query(0, ge=0, le=1),
    chaos_fanatic: Optional[int] = Query(0, ge=0, le=1),
    commander_zilyana: Optional[int] = Query(0, ge=0, le=1),
    corporeal_beast: Optional[int] = Query(0, ge=0, le=1),
    dagannoth_prime: Optional[int] = Query(0, ge=0, le=1),
    dagannoth_rex: Optional[int] = Query(0, ge=0, le=1),
    dagannoth_supreme: Optional[int] = Query(0, ge=0, le=1),
    crazy_archaeologist: Optional[int] = Query(0, ge=0, le=1),
    deranged_archaeologist: Optional[int] = Query(0, ge=0, le=1),
    general_graardor: Optional[int] = Query(0, ge=0, le=1),
    giant_mole: Optional[int] = Query(0, ge=0, le=1),
    grotesque_guardians: Optional[int] = Query(0, ge=0, le=1),
    hespori: Optional[int] = Query(0, ge=0, le=1),
    kalphite_queen: Optional[int] = Query(0, ge=0, le=1),
    king_black_dragon: Optional[int] = Query(0, ge=0, le=1),
    kraken: Optional[int] = Query(0, ge=0, le=1),
    kreearra: Optional[int] = Query(0, ge=0, le=1),
    kril_tsutsaroth: Optional[int] = Query(0, ge=0, le=1),
    mimic: Optional[int] = Query(0, ge=0, le=1),
    nex: Optional[int] = Query(0, ge=0, le=1),
    nightmare: Optional[int] = Query(0, ge=0, le=1),
    phosanis_nightmare: Optional[int] = Query(0, ge=0, le=1),
    obor: Optional[int] = Query(0, ge=0, le=1),
    sarachnis: Optional[int] = Query(0, ge=0, le=1),
    scorpia: Optional[int] = Query(0, ge=0, le=1),
    skotizo: Optional[int] = Query(0, ge=0, le=1),
    tempoross: Optional[int] = Query(0, ge=0, le=1),
    the_gauntlet: Optional[int] = Query(0, ge=0, le=1),
    the_corrupted_gauntlet: Optional[int] = Query(0, ge=0, le=1),
    theatre_of_blood: Optional[int] = Query(0, ge=0, le=1),
    theatre_of_blood_hard_mode: Optional[int] = Query(0, ge=0, le=1),
    thermonuclear_smoke_devil: Optional[int] = Query(0, ge=0, le=1),
    tzkal_zuk: Optional[int] = Query(0, ge=0, le=1),
    tztok_jad: Optional[int] = Query(0, ge=0, le=1),
    venenatis: Optional[int] = Query(0, ge=0, le=1),
    vetion: Optional[int] = Query(0, ge=0, le=1),
    vorkath: Optional[int] = Query(0, ge=0, le=1),
    wintertodt: Optional[int] = Query(0, ge=0, le=1),
    zalcano: Optional[int] = Query(0, ge=0, le=1),
    zulrah: Optional[int] = Query(0, ge=0, le=1),
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    table = OptionsBoss
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if user_id is not None:
        sql = sql.where(table.user_id == user_id)

    if token is not None:
        sql = sql.where(table.token == token)

    if abyssal_sire is not None:
        sql = sql.where(table.abyssal_sire == abyssal_sire)

    if alchemical_hydra is not None:
        sql = sql.where(table.alchemical_hydra == alchemical_hydra)

    if barrows_chests is not None:
        sql = sql.where(table.barrows_chests == barrows_chests)

    if bryophyta is not None:
        sql = sql.where(table.bryophyta == bryophyta)

    if callisto is not None:
        sql = sql.where(table.callisto == callisto)

    if cerberus is not None:
        sql = sql.where(table.cerberus == cerberus)

    if chambers_of_xeric is not None:
        sql = sql.where(table.chambers_of_xeric == chambers_of_xeric)

    if chambers_of_xeric_challenge_mode is not None:
        sql = sql.where(table.chambers_of_xeric_challenge_mode ==
                        chambers_of_xeric_challenge_mode)

    if chaos_elemental is not None:
        sql = sql.where(table.chaos_elemental == chaos_elemental)

    if chaos_fanatic is not None:
        sql = sql.where(table.chaos_fanatic == chaos_fanatic)

    if commander_zilyana is not None:
        sql = sql.where(table.commander_zilyana == commander_zilyana)

    if corporeal_beast is not None:
        sql = sql.where(table.corporeal_beast == corporeal_beast)

    if dagannoth_prime is not None:
        sql = sql.where(table.dagannoth_prime == dagannoth_prime)

    if dagannoth_rex is not None:
        sql = sql.where(table.dagannoth_rex == dagannoth_rex)

    if dagannoth_supreme is not None:
        sql = sql.where(table.dagannoth_supreme == dagannoth_supreme)

    if crazy_archaeologist is not None:
        sql = sql.where(table.crazy_archaeologist == crazy_archaeologist)

    if deranged_archaeologist is not None:
        sql = sql.where(table.deranged_archaeologist == deranged_archaeologist)

    if general_graardor is not None:
        sql = sql.where(table.general_graardor == general_graardor)

    if giant_mole is not None:
        sql = sql.where(table.giant_mole == giant_mole)

    if grotesque_guardians is not None:
        sql = sql.where(table.grotesque_guardians == grotesque_guardians)

    if hespori is not None:
        sql = sql.where(table.hespori == hespori)

    if kalphite_queen is not None:
        sql = sql.where(table.kalphite_queen == kalphite_queen)

    if king_black_dragon is not None:
        sql = sql.where(table.king_black_dragon == king_black_dragon)

    if kraken is not None:
        sql = sql.where(table.kraken == kraken)

    if kreearra is not None:
        sql = sql.where(table.kreearra == kreearra)

    if kril_tsutsaroth is not None:
        sql = sql.where(table.kril_tsutsaroth == kril_tsutsaroth)

    if mimic is not None:
        sql = sql.where(table.mimic == mimic)

    if nex is not None:
        sql = sql.where(table.nex == nex)

    if nightmare is not None:
        sql = sql.where(table.nightmare == nightmare)

    if phosanis_nightmare is not None:
        sql = sql.where(table.phosanis_nightmare == phosanis_nightmare)

    if obor is not None:
        sql = sql.where(table.obor == obor)

    if sarachnis is not None:
        sql = sql.where(table.sarachnis == sarachnis)

    if scorpia is not None:
        sql = sql.where(table.scorpia == scorpia)

    if skotizo is not None:
        sql = sql.where(table.skotizo == skotizo)

    if tempoross is not None:
        sql = sql.where(table.tempoross == tempoross)

    if the_gauntlet is not None:
        sql = sql.where(table.the_gauntlet == the_gauntlet)

    if the_corrupted_gauntlet is not None:
        sql = sql.where(table.the_corrupted_gauntlet == the_corrupted_gauntlet)

    if theatre_of_blood is not None:
        sql = sql.where(table.theatre_of_blood == theatre_of_blood)

    if theatre_of_blood_hard_mode is not None:
        sql = sql.where(table.theatre_of_blood_hard_mode ==
                        theatre_of_blood_hard_mode)

    if thermonuclear_smoke_devil is not None:
        sql = sql.where(table.thermonuclear_smoke_devil ==
                        thermonuclear_smoke_devil)

    if tzkal_zuk is not None:
        sql = sql.where(table.tzkal_zuk == tzkal_zuk)

    if tztok_jad is not None:
        sql = sql.where(table.tztok_jad == tztok_jad)

    if venenatis is not None:
        sql = sql.where(table.venenatis == venenatis)

    if vetion is not None:
        sql = sql.where(table.vetion == vetion)

    if vorkath is not None:
        sql = sql.where(table.vorkath == vorkath)

    if wintertodt is not None:
        sql = sql.where(table.wintertodt == wintertodt)

    if zalcano is not None:
        sql = sql.where(table.zalcano == zalcano)

    if zulrah is not None:
        sql = sql.where(table.zulrah == zulrah)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/options-boss", tags=["options", "boss"])
async def post_options_boss(login: str, token: str, options_boss: options_boss) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    values = options_boss.dict()
    table = options_boss
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
