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
from api.database.models import OptionsMinigame
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


class options_minigame(BaseModel):
    """
    Options minigame base model containing the types and content expected by the database
    """

    ID: Optional[int]
    user_id: int
    barbarian_assault: Optional[int]
    blast_furnace: Optional[int]
    burthorpe_games_room: Optional[int]
    castle_wars: Optional[int]
    clan_wars: Optional[int]
    dagannoth_kings: Optional[int]
    fishing_trawler: Optional[int]
    god_wars: Optional[int]
    guardians_of_the_rift: Optional[int]
    last_man_standing: Optional[int]
    nightmare_zone: Optional[int]
    pest_control: Optional[int]
    player_owned_houses: Optional[int]
    rat_pits: Optional[int]
    shades_of_mortton: Optional[int]
    shield_of_arrav: Optional[int]
    shooting_stars: Optional[int]
    soul_wars: Optional[int]
    theatre_of_blood: Optional[int]
    tithe_farm: Optional[int]
    trouble_brewing: Optional[int]
    tzhaar_fight_pit: Optional[int]
    volcanic_mine: Optional[int]


@router.get("/V1/options-minigame/", tags=["options", "minigame"])
async def get_options_minigame(
    login: str,
    token: Optional[int] = None,
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    barbarian_assault: Optional[int] = Query(0, ge=0, le=1),
    blast_furnace: Optional[int] = Query(0, ge=0, le=1),
    burthorpe_games_room: Optional[int] = Query(0, ge=0, le=1),
    castle_wars: Optional[int] = Query(0, ge=0, le=1),
    clan_wars: Optional[int] = Query(0, ge=0, le=1),
    dagannoth_kings: Optional[int] = Query(0, ge=0, le=1),
    fishing_trawler: Optional[int] = Query(0, ge=0, le=1),
    god_wars: Optional[int] = Query(0, ge=0, le=1),
    guardians_of_the_rift: Optional[int] = Query(0, ge=0, le=1),
    last_man_standing: Optional[int] = Query(0, ge=0, le=1),
    nightmare_zone: Optional[int] = Query(0, ge=0, le=1),
    pest_control: Optional[int] = Query(0, ge=0, le=1),
    player_owned_houses: Optional[int] = Query(0, ge=0, le=1),
    rat_pits: Optional[int] = Query(0, ge=0, le=1),
    shades_of_mortton: Optional[int] = Query(0, ge=0, le=1),
    shield_of_arrav: Optional[int] = Query(0, ge=0, le=1),
    shooting_stars: Optional[int] = Query(0, ge=0, le=1),
    soul_wars: Optional[int] = Query(0, ge=0, le=1),
    theatre_of_blood: Optional[int] = Query(0, ge=0, le=1),
    tithe_farm: Optional[int] = Query(0, ge=0, le=1),
    trouble_brewing: Optional[int] = Query(0, ge=0, le=1),
    tzhaar_fight_pit: Optional[int] = Query(0, ge=0, le=1),
    volcanic_mine: Optional[int] = Query(0, ge=0, le=1),
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    table = OptionsMinigame
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)

    if user_id is not None:
        sql = sql.where(table.user_id == user_id)

    if token is not None:
        sql = sql.where(table.token == token)

    if barbarian_assault is not None:
        sql = sql.where(table.barbarian_assault == barbarian_assault)

    if blast_furnace is not None:
        sql = sql.where(table.blast_furnace == blast_furnace)

    if burthorpe_games_room is not None:
        sql = sql.where(table.burthorpe_games_room == burthorpe_games_room)

    if castle_wars is not None:
        sql = sql.where(table.castle_wars == castle_wars)

    if clan_wars is not None:
        sql = sql.where(table.clan_wars == clan_wars)

    if dagannoth_kings is not None:
        sql = sql.where(table.dagannoth_kings == dagannoth_kings)

    if fishing_trawler is not None:
        sql = sql.where(table.fishing_trawler == fishing_trawler)

    if god_wars is not None:
        sql = sql.where(table.god_wars == god_wars)

    if guardians_of_the_rift is not None:
        sql = sql.where(table.guardians_of_the_rift == guardians_of_the_rift)

    if last_man_standing is not None:
        sql = sql.where(table.last_man_standing == last_man_standing)

    if nightmare_zone is not None:
        sql = sql.where(table.nightmare_zone == nightmare_zone)

    if pest_control is not None:
        sql = sql.where(table.pest_control == pest_control)

    if player_owned_houses is not None:
        sql = sql.where(table.player_owned_houses == player_owned_houses)

    if rat_pits is not None:
        sql = sql.where(table.rat_pits == rat_pits)

    if shades_of_mortton is not None:
        sql = sql.where(table.shades_of_mortton == shades_of_mortton)

    if shield_of_arrav is not None:
        sql = sql.where(table.shield_of_arrav == shield_of_arrav)

    if shooting_stars is not None:
        sql = sql.where(table.shooting_stars == shooting_stars)

    if soul_wars is not None:
        sql = sql.where(table.soul_wars == soul_wars)

    if theatre_of_blood is not None:
        sql = sql.where(table.theatre_of_blood == theatre_of_blood)

    if tithe_farm is not None:
        sql = sql.where(table.tithe_farm == tithe_farm)

    if trouble_brewing is not None:
        sql = sql.where(table.trouble_brewing == trouble_brewing)

    if tzhaar_fight_pit is not None:
        sql = sql.where(table.tzhaar_fight_pit == tzhaar_fight_pit)

    if volcanic_mine is not None:
        sql = sql.where(table.volcanic_mine == volcanic_mine)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/options-minigame", tags=["options", "minigame"])
async def post_options_minigame(
    login: str, token: str, options_minigame: options_minigame
) -> json:

    if not await verify_token(login=login, token=token, access_level=9):
        return

    values = options_minigame.dict()
    table = options_minigame
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"ok": "ok"}
