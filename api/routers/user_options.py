from ast import Delete
import json
from cgitb import text
from dataclasses import replace
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional
import time
from urllib.request import Request
from certifi import where

from pymysql import Timestamp

from api.database.functions import (
    USERDATA_ENGINE,
    EngineType,
    sqlalchemy_result,
    verify_token,
    verify_user_agent,
)
from api.database.models import UserOptions
from fastapi import APIRouter, Header, HTTPException, Query, status
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pyparsing import Opt
from requests import delete, options, request
from sqlalchemy import TIMESTAMP, select
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import Select, insert, select, update

router = APIRouter()


class user_id(BaseModel):
    user_id: int


class user_options(BaseModel):
    """
    Options skill base model containing the types and content expected by the database
    """

    user_id: Optional[int]
    in_queue: bool = Query(False)
    ATTACK: bool = Query(False)
    STRENGTH: bool = Query(False)
    DEFENCE: bool = Query(False)
    HITPOINTS: bool = Query(False)
    RANGED: bool = Query(False)
    PRAYER: bool = Query(False)
    MAGIC: bool = Query(False)
    COOKING: bool = Query(False)
    WOODCUTTING: bool = Query(False)
    FLETCHING: bool = Query(False)
    FISHING: bool = Query(False)
    FIREMAKING: bool = Query(False)
    CRAFTING: bool = Query(False)
    SMITHING: bool = Query(False)
    MINING: bool = Query(False)
    HERBLORE: bool = Query(False)
    AGILITY: bool = Query(False)
    THIEVING: bool = Query(False)
    SLAYER: bool = Query(False)
    FARMING: bool = Query(False)
    RUNECRAFT: bool = Query(False)
    HUNTER: bool = Query(False)
    CONSTRUCTION: bool = Query(False)
    ALL_SKILLS: bool = Query(False)
    ABYSSAL_SIRE: bool = Query(False)
    ALCHEMICAL_HYDRA: bool = Query(False)
    BRYOPHYTA: bool = Query(False)
    CERBERUS: bool = Query(False)
    GROTESQUE_GUARDIANS: bool = Query(False)
    HESPORI: bool = Query(False)
    KRAKEN: bool = Query(False)
    MIMIC: bool = Query(False)
    OBOR: bool = Query(False)
    PHOSANIS_NIGHTMARE: bool = Query(False)
    SKOTIZO: bool = Query(False)
    GAUNTLET: bool = Query(False)
    GAUNTLET_CORRUPTED: bool = Query(False)
    THERMONUCLEARSMOKEDEVIL: bool = Query(False)
    TZ_KAL_ZUK: bool = Query(False)
    TZ_TOK_JAD: bool = Query(False)
    VORKATH: bool = Query(False)
    ZULRAH: bool = Query(False)
    BARROWS: bool = Query(False)
    CALLISTO: bool = Query(False)
    CHAOS_ELEMENTAL: bool = Query(False)
    CHAOS_FANATIC: bool = Query(False)
    COMMANDER_ZILYANA: bool = Query(False)
    CORPOREAL_BEAST: bool = Query(False)
    ARCHAEOLOGIST_CRAZY: bool = Query(False)
    ARCHAEOLOGIST_DERANGED: bool = Query(False)
    DAGANNOTH_PRIME: bool = Query(False)
    DAGANNOTH_REX: bool = Query(False)
    DAGANNOTH_SUPREME: bool = Query(False)
    GENERAL_GRAARDOR: bool = Query(False)
    GIANT_MOLE: bool = Query(False)
    KALPHITE_QUEEN: bool = Query(False)
    KING_BLACK_DRAGON: bool = Query(False)
    KREEARRA: bool = Query(False)
    KRIL_TSUTSAROTH: bool = Query(False)
    NEX: bool = Query(False)
    NIGHTMARE: bool = Query(False)
    SARACHNIS: bool = Query(False)
    SCORPIA: bool = Query(False)
    VENENATIS: bool = Query(False)
    VETION: bool = Query(False)
    ZALCANO: bool = Query(False)
    BARBARIAN_ASSAULT: bool = Query(False)
    BLAST_FURNACE: bool = Query(False)
    BLAST_MINE: bool = Query(False)
    BRIMHAVEN_AGILITY_ARENA: bool = Query(False)
    BOUNTY_HUNTER_HUNTER: bool = Query(False)
    BOUNTY_HUNTER_ROGUE: bool = Query(False)
    CAMDOZAAL_VAULT: bool = Query(False)
    CASTLE_WARS: bool = Query(False)
    CLAN_WARS: bool = Query(False)
    CREATURE_CREATION: bool = Query(False)
    DUEL_ARENA: bool = Query(False)
    FISHING_TRAWLER: bool = Query(False)
    GNOME_BALL: bool = Query(False)
    GNOME_RESTAURANT: bool = Query(False)
    GUARDIANS_OF_THE_RIFT: bool = Query(False)
    HALLOWED_SEPULCHRE: bool = Query(False)
    PURO_PURO: bool = Query(False)
    MAGE_ARENA: bool = Query(False)
    MAHOGANY_HOMES: bool = Query(False)
    MAGE_TRAINING_ARENA: bool = Query(False)
    NIGHTMARE_ZONE: bool = Query(False)
    ORGANIZED_CRIME: bool = Query(False)
    PEST_CONTROL: bool = Query(False)
    PYRAMID_PLUNDER: bool = Query(False)
    ROGUES_DEN: bool = Query(False)
    SHADES_OF_MORTON: bool = Query(False)
    SORCERESS_GARDEN: bool = Query(False)
    TAI_BWO_WANNAI: bool = Query(False)
    TITHE_FARM: bool = Query(False)
    TROUBLE_BREWING: bool = Query(False)
    UNDERWATER_AGILITY_AND_THIEVING: bool = Query(False)
    VOLCANIC_MINE: bool = Query(False)
    LAST_MAN_STANDING: bool = Query(False)
    SOUL_WARS: bool = Query(False)
    TEMPOROSS: bool = Query(False)
    WINTERTODT: bool = Query(False)
    COX: bool = Query(False)
    HARD_COX: bool = Query(False)
    TOB: bool = Query(False)
    HARD_TOB: bool = Query(False)
    CLUES: bool = Query(False)
    FALADOR_PARTY_ROOM: bool = Query(False)
    PVP_GENERIC: bool = Query(False)


@router.get("/V1/user-options/", tags=["user"])
async def get_user_options(
    # User Items
    login: str = Query(..., min_length=1, max_length=12),
    token: str = Query(..., min_length=32, max_length=32),
    user_agent: str | None = Header(default=None),
    # Table items
    ID: Optional[int] = None,
    user_id: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    in_queue: Optional[bool] = Query(False),
    ATTACK: Optional[bool] = Query(False),
    STRENGTH: Optional[bool] = Query(False),
    DEFENCE: Optional[bool] = Query(False),
    HITPOINTS: Optional[bool] = Query(False),
    RANGED: Optional[bool] = Query(False),
    PRAYER: Optional[bool] = Query(False),
    MAGIC: Optional[bool] = Query(False),
    COOKING: Optional[bool] = Query(False),
    WOODCUTTING: Optional[bool] = Query(False),
    FLETCHING: Optional[bool] = Query(False),
    FISHING: Optional[bool] = Query(False),
    FIREMAKING: Optional[bool] = Query(False),
    CRAFTING: Optional[bool] = Query(False),
    SMITHING: Optional[bool] = Query(False),
    MINING: Optional[bool] = Query(False),
    HERBLORE: Optional[bool] = Query(False),
    AGILITY: Optional[bool] = Query(False),
    THIEVING: Optional[bool] = Query(False),
    SLAYER: Optional[bool] = Query(False),
    FARMING: Optional[bool] = Query(False),
    RUNECRAFT: Optional[bool] = Query(False),
    HUNTER: Optional[bool] = Query(False),
    CONSTRUCTION: Optional[bool] = Query(False),
    ALL_SKILLS: Optional[bool] = Query(False),
    ABYSSAL_SIRE: Optional[bool] = Query(False),
    ALCHEMICAL_HYDRA: Optional[bool] = Query(False),
    BRYOPHYTA: Optional[bool] = Query(False),
    CERBERUS: Optional[bool] = Query(False),
    GROTESQUE_GUARDIANS: Optional[bool] = Query(False),
    HESPORI: Optional[bool] = Query(False),
    KRAKEN: Optional[bool] = Query(False),
    MIMIC: Optional[bool] = Query(False),
    OBOR: Optional[bool] = Query(False),
    PHOSANIS_NIGHTMARE: Optional[bool] = Query(False),
    SKOTIZO: Optional[bool] = Query(False),
    GAUNTLET: Optional[bool] = Query(False),
    GAUNTLET_CORRUPTED: Optional[bool] = Query(False),
    THERMONUCLEARSMOKEDEVIL: Optional[bool] = Query(False),
    TZ_KAL_ZUK: Optional[bool] = Query(False),
    TZ_TOK_JAD: Optional[bool] = Query(False),
    VORKATH: Optional[bool] = Query(False),
    ZULRAH: Optional[bool] = Query(False),
    BARROWS: Optional[bool] = Query(False),
    CALLISTO: Optional[bool] = Query(False),
    CHAOS_ELEMENTAL: Optional[bool] = Query(False),
    CHAOS_FANATIC: Optional[bool] = Query(False),
    COMMANDER_ZILYANA: Optional[bool] = Query(False),
    CORPOREAL_BEAST: Optional[bool] = Query(False),
    ARCHAEOLOGIST_CRAZY: Optional[bool] = Query(False),
    ARCHAEOLOGIST_DERANGED: Optional[bool] = Query(False),
    DAGANNOTH_PRIME: Optional[bool] = Query(False),
    DAGANNOTH_REX: Optional[bool] = Query(False),
    DAGANNOTH_SUPREME: Optional[bool] = Query(False),
    GENERAL_GRAARDOR: Optional[bool] = Query(False),
    GIANT_MOLE: Optional[bool] = Query(False),
    KALPHITE_QUEEN: Optional[bool] = Query(False),
    KING_BLACK_DRAGON: Optional[bool] = Query(False),
    KREEARRA: Optional[bool] = Query(False),
    KRIL_TSUTSAROTH: Optional[bool] = Query(False),
    NEX: Optional[bool] = Query(False),
    NIGHTMARE: Optional[bool] = Query(False),
    SARACHNIS: Optional[bool] = Query(False),
    SCORPIA: Optional[bool] = Query(False),
    VENENATIS: Optional[bool] = Query(False),
    VETION: Optional[bool] = Query(False),
    ZALCANO: Optional[bool] = Query(False),
    BARBARIAN_ASSAULT: Optional[bool] = Query(False),
    BLAST_FURNACE: Optional[bool] = Query(False),
    BLAST_MINE: Optional[bool] = Query(False),
    BRIMHAVEN_AGILITY_ARENA: Optional[bool] = Query(False),
    BOUNTY_HUNTER_HUNTER: Optional[bool] = Query(False),
    BOUNTY_HUNTER_ROGUE: Optional[bool] = Query(False),
    CAMDOZAAL_VAULT: Optional[bool] = Query(False),
    CASTLE_WARS: Optional[bool] = Query(False),
    CLAN_WARS: Optional[bool] = Query(False),
    CREATURE_CREATION: Optional[bool] = Query(False),
    DUEL_ARENA: Optional[bool] = Query(False),
    FISHING_TRAWLER: Optional[bool] = Query(False),
    GNOME_BALL: Optional[bool] = Query(False),
    GNOME_RESTAURANT: Optional[bool] = Query(False),
    GUARDIANS_OF_THE_RIFT: Optional[bool] = Query(False),
    HALLOWED_SEPULCHRE: Optional[bool] = Query(False),
    PURO_PURO: Optional[bool] = Query(False),
    MAGE_ARENA: Optional[bool] = Query(False),
    MAHOGANY_HOMES: Optional[bool] = Query(False),
    MAGE_TRAINING_ARENA: Optional[bool] = Query(False),
    NIGHTMARE_ZONE: Optional[bool] = Query(False),
    ORGANIZED_CRIME: Optional[bool] = Query(False),
    PEST_CONTROL: Optional[bool] = Query(False),
    PYRAMID_PLUNDER: Optional[bool] = Query(False),
    ROGUES_DEN: Optional[bool] = Query(False),
    SHADES_OF_MORTON: Optional[bool] = Query(False),
    SORCERESS_GARDEN: Optional[bool] = Query(False),
    TAI_BWO_WANNAI: Optional[bool] = Query(False),
    TITHE_FARM: Optional[bool] = Query(False),
    TROUBLE_BREWING: Optional[bool] = Query(False),
    UNDERWATER_AGILITY_AND_THIEVING: Optional[bool] = Query(False),
    VOLCANIC_MINE: Optional[bool] = Query(False),
    LAST_MAN_STANDING: Optional[bool] = Query(False),
    SOUL_WARS: Optional[bool] = Query(False),
    TEMPOROSS: Optional[bool] = Query(False),
    WINTERTODT: Optional[bool] = Query(False),
    COX: Optional[bool] = Query(False),
    HARD_COX: Optional[bool] = Query(False),
    TOB: Optional[bool] = Query(False),
    HARD_TOB: Optional[bool] = Query(False),
    CLUES: Optional[bool] = Query(False),
    FALADOR_PARTY_ROOM: Optional[bool] = Query(False),
    PVP_GENERIC: Optional[bool] = Query(False),
    row_count: Optional[int] = Query(100, ge=1, le=1000),
    page: Optional[int] = Query(1, ge=1),
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    if not await verify_token(login=login, token=token, access_level=0):
        return

    table = UserOptions
    sql: Select = select(table)

    if ID is not None:
        sql = sql.where(table.ID == ID)
    if user_id is not None:
        sql = sql.where(table.user_id == user_id)
    if timestamp is not None:
        sql = sql.where(table.timestamp == timestamp)
    if in_queue is not None:
        sql = sql.where(table.in_queue == in_queue)
    if token is not None:
        sql = sql.where(table.token == token)

    if ATTACK is not None:
        sql = sql.where(table.ATTACK == ATTACK)
    if STRENGTH is not None:
        sql = sql.where(table.STRENGTH == STRENGTH)
    if DEFENCE is not None:
        sql = sql.where(table.DEFENCE == DEFENCE)
    if HITPOINTS is not None:
        sql = sql.where(table.HITPOINTS == HITPOINTS)
    if RANGED is not None:
        sql = sql.where(table.RANGED == RANGED)
    if PRAYER is not None:
        sql = sql.where(table.PRAYER == PRAYER)
    if MAGIC is not None:
        sql = sql.where(table.MAGIC == MAGIC)
    if COOKING is not None:
        sql = sql.where(table.COOKING == COOKING)
    if WOODCUTTING is not None:
        sql = sql.where(table.WOODCUTTING == WOODCUTTING)
    if FLETCHING is not None:
        sql = sql.where(table.FLETCHING == FLETCHING)
    if FISHING is not None:
        sql = sql.where(table.FISHING == FISHING)
    if FIREMAKING is not None:
        sql = sql.where(table.FIREMAKING == FIREMAKING)
    if CRAFTING is not None:
        sql = sql.where(table.CRAFTING == CRAFTING)
    if SMITHING is not None:
        sql = sql.where(table.SMITHING == SMITHING)
    if MINING is not None:
        sql = sql.where(table.MINING == MINING)
    if HERBLORE is not None:
        sql = sql.where(table.HERBLORE == HERBLORE)
    if AGILITY is not None:
        sql = sql.where(table.AGILITY == AGILITY)
    if THIEVING is not None:
        sql = sql.where(table.THIEVING == THIEVING)
    if SLAYER is not None:
        sql = sql.where(table.SLAYER == SLAYER)
    if FARMING is not None:
        sql = sql.where(table.FARMING == FARMING)
    if RUNECRAFT is not None:
        sql = sql.where(table.RUNECRAFT == RUNECRAFT)
    if HUNTER is not None:
        sql = sql.where(table.HUNTER == HUNTER)
    if CONSTRUCTION is not None:
        sql = sql.where(table.CONSTRUCTION == CONSTRUCTION)
    if ALL_SKILLS is not None:
        sql = sql.where(table.ALL_SKILLS == ALL_SKILLS)
    if ABYSSAL_SIRE is not None:
        sql = sql.where(table.ABYSSAL_SIRE == ABYSSAL_SIRE)
    if ALCHEMICAL_HYDRA is not None:
        sql = sql.where(table.ALCHEMICAL_HYDRA == ALCHEMICAL_HYDRA)
    if BRYOPHYTA is not None:
        sql = sql.where(table.BRYOPHYTA == BRYOPHYTA)
    if CERBERUS is not None:
        sql = sql.where(table.CERBERUS == CERBERUS)
    if GROTESQUE_GUARDIANS is not None:
        sql = sql.where(table.GROTESQUE_GUARDIANS == GROTESQUE_GUARDIANS)
    if HESPORI is not None:
        sql = sql.where(table.HESPORI == HESPORI)
    if KRAKEN is not None:
        sql = sql.where(table.KRAKEN == KRAKEN)
    if MIMIC is not None:
        sql = sql.where(table.MIMIC == MIMIC)
    if OBOR is not None:
        sql = sql.where(table.OBOR == OBOR)
    if PHOSANIS_NIGHTMARE is not None:
        sql = sql.where(table.PHOSANIS_NIGHTMARE == PHOSANIS_NIGHTMARE)
    if SKOTIZO is not None:
        sql = sql.where(table.SKOTIZO == SKOTIZO)
    if GAUNTLET is not None:
        sql = sql.where(table.GAUNTLET == GAUNTLET)
    if GAUNTLET_CORRUPTED is not None:
        sql = sql.where(table.GAUNTLET_CORRUPTED == GAUNTLET_CORRUPTED)
    if THERMONUCLEARSMOKEDEVIL is not None:
        sql = sql.where(table.THERMONUCLEARSMOKEDEVIL == THERMONUCLEARSMOKEDEVIL)
    if TZ_KAL_ZUK is not None:
        sql = sql.where(table.TZ_KAL_ZUK == TZ_KAL_ZUK)
    if TZ_TOK_JAD is not None:
        sql = sql.where(table.TZ_TOK_JAD == TZ_TOK_JAD)
    if VORKATH is not None:
        sql = sql.where(table.VORKATH == VORKATH)
    if ZULRAH is not None:
        sql = sql.where(table.ZULRAH == ZULRAH)
    if BARROWS is not None:
        sql = sql.where(table.BARROWS == BARROWS)
    if CALLISTO is not None:
        sql = sql.where(table.CALLISTO == CALLISTO)
    if CHAOS_ELEMENTAL is not None:
        sql = sql.where(table.CHAOS_ELEMENTAL == CHAOS_ELEMENTAL)
    if CHAOS_FANATIC is not None:
        sql = sql.where(table.CHAOS_FANATIC == CHAOS_FANATIC)
    if COMMANDER_ZILYANA is not None:
        sql = sql.where(table.COMMANDER_ZILYANA == COMMANDER_ZILYANA)
    if CORPOREAL_BEAST is not None:
        sql = sql.where(table.CORPOREAL_BEAST == CORPOREAL_BEAST)
    if ARCHAEOLOGIST_CRAZY is not None:
        sql = sql.where(table.ARCHAEOLOGIST_CRAZY == ARCHAEOLOGIST_CRAZY)
    if ARCHAEOLOGIST_DERANGED is not None:
        sql = sql.where(table.ARCHAEOLOGIST_DERANGED == ARCHAEOLOGIST_DERANGED)
    if DAGANNOTH_PRIME is not None:
        sql = sql.where(table.DAGANNOTH_PRIME == DAGANNOTH_PRIME)
    if DAGANNOTH_REX is not None:
        sql = sql.where(table.DAGANNOTH_REX == DAGANNOTH_REX)
    if DAGANNOTH_SUPREME is not None:
        sql = sql.where(table.DAGANNOTH_SUPREME == DAGANNOTH_SUPREME)
    if GENERAL_GRAARDOR is not None:
        sql = sql.where(table.GENERAL_GRAARDOR == GENERAL_GRAARDOR)
    if GIANT_MOLE is not None:
        sql = sql.where(table.GIANT_MOLE == GIANT_MOLE)
    if KALPHITE_QUEEN is not None:
        sql = sql.where(table.KALPHITE_QUEEN == KALPHITE_QUEEN)
    if KING_BLACK_DRAGON is not None:
        sql = sql.where(table.KING_BLACK_DRAGON == KING_BLACK_DRAGON)
    if KREEARRA is not None:
        sql = sql.where(table.KREEARRA == KREEARRA)
    if KRIL_TSUTSAROTH is not None:
        sql = sql.where(table.KRIL_TSUTSAROTH == KRIL_TSUTSAROTH)
    if NEX is not None:
        sql = sql.where(table.NEX == NEX)
    if NIGHTMARE is not None:
        sql = sql.where(table.NIGHTMARE == NIGHTMARE)
    if SARACHNIS is not None:
        sql = sql.where(table.SARACHNIS == SARACHNIS)
    if SCORPIA is not None:
        sql = sql.where(table.SCORPIA == SCORPIA)
    if VENENATIS is not None:
        sql = sql.where(table.VENENATIS == VENENATIS)
    if VETION is not None:
        sql = sql.where(table.VETION == VETION)
    if ZALCANO is not None:
        sql = sql.where(table.ZALCANO == ZALCANO)
    if BARBARIAN_ASSAULT is not None:
        sql = sql.where(table.BARBARIAN_ASSAULT == BARBARIAN_ASSAULT)
    if BLAST_FURNACE is not None:
        sql = sql.where(table.BLAST_FURNACE == BLAST_FURNACE)
    if BLAST_MINE is not None:
        sql = sql.where(table.BLAST_MINE == BLAST_MINE)
    if BRIMHAVEN_AGILITY_ARENA is not None:
        sql = sql.where(table.BRIMHAVEN_AGILITY_ARENA == BRIMHAVEN_AGILITY_ARENA)
    if BOUNTY_HUNTER_HUNTER is not None:
        sql = sql.where(table.BOUNTY_HUNTER_HUNTER == BOUNTY_HUNTER_HUNTER)
    if BOUNTY_HUNTER_ROGUE is not None:
        sql = sql.where(table.BOUNTY_HUNTER_ROGUE == BOUNTY_HUNTER_ROGUE)
    if CAMDOZAAL_VAULT is not None:
        sql = sql.where(table.CAMDOZAAL_VAULT == CAMDOZAAL_VAULT)
    if CASTLE_WARS is not None:
        sql = sql.where(table.CASTLE_WARS == CASTLE_WARS)
    if CLAN_WARS is not None:
        sql = sql.where(table.CLAN_WARS == CLAN_WARS)
    if CREATURE_CREATION is not None:
        sql = sql.where(table.CREATURE_CREATION == CREATURE_CREATION)
    if DUEL_ARENA is not None:
        sql = sql.where(table.DUEL_ARENA == DUEL_ARENA)
    if FISHING_TRAWLER is not None:
        sql = sql.where(table.FISHING_TRAWLER == FISHING_TRAWLER)
    if GNOME_BALL is not None:
        sql = sql.where(table.GNOME_BALL == GNOME_BALL)
    if GNOME_RESTAURANT is not None:
        sql = sql.where(table.GNOME_RESTAURANT == GNOME_RESTAURANT)
    if GUARDIANS_OF_THE_RIFT is not None:
        sql = sql.where(table.GUARDIANS_OF_THE_RIFT == GUARDIANS_OF_THE_RIFT)
    if HALLOWED_SEPULCHRE is not None:
        sql = sql.where(table.HALLOWED_SEPULCHRE == HALLOWED_SEPULCHRE)
    if PURO_PURO is not None:
        sql = sql.where(table.PURO_PURO == PURO_PURO)
    if MAGE_ARENA is not None:
        sql = sql.where(table.MAGE_ARENA == MAGE_ARENA)
    if MAHOGANY_HOMES is not None:
        sql = sql.where(table.MAHOGANY_HOMES == MAHOGANY_HOMES)
    if MAGE_TRAINING_ARENA is not None:
        sql = sql.where(table.MAGE_TRAINING_ARENA == MAGE_TRAINING_ARENA)
    if NIGHTMARE_ZONE is not None:
        sql = sql.where(table.NIGHTMARE_ZONE == NIGHTMARE_ZONE)
    if ORGANIZED_CRIME is not None:
        sql = sql.where(table.ORGANIZED_CRIME == ORGANIZED_CRIME)
    if PEST_CONTROL is not None:
        sql = sql.where(table.PEST_CONTROL == PEST_CONTROL)
    if PYRAMID_PLUNDER is not None:
        sql = sql.where(table.PYRAMID_PLUNDER == PYRAMID_PLUNDER)
    if ROGUES_DEN is not None:
        sql = sql.where(table.ROGUES_DEN == ROGUES_DEN)
    if SHADES_OF_MORTON is not None:
        sql = sql.where(table.SHADES_OF_MORTON == SHADES_OF_MORTON)
    if SORCERESS_GARDEN is not None:
        sql = sql.where(table.SORCERESS_GARDEN == SORCERESS_GARDEN)
    if TAI_BWO_WANNAI is not None:
        sql = sql.where(table.TAI_BWO_WANNAI == TAI_BWO_WANNAI)
    if TITHE_FARM is not None:
        sql = sql.where(table.TITHE_FARM == TITHE_FARM)
    if TROUBLE_BREWING is not None:
        sql = sql.where(table.TROUBLE_BREWING == TROUBLE_BREWING)
    if UNDERWATER_AGILITY_AND_THIEVING is not None:
        sql = sql.where(
            table.UNDERWATER_AGILITY_AND_THIEVING == UNDERWATER_AGILITY_AND_THIEVING
        )
    if VOLCANIC_MINE is not None:
        sql = sql.where(table.VOLCANIC_MINE == VOLCANIC_MINE)
    if LAST_MAN_STANDING is not None:
        sql = sql.where(table.LAST_MAN_STANDING == LAST_MAN_STANDING)
    if SOUL_WARS is not None:
        sql = sql.where(table.SOUL_WARS == SOUL_WARS)
    if TEMPOROSS is not None:
        sql = sql.where(table.TEMPOROSS == TEMPOROSS)
    if WINTERTODT is not None:
        sql = sql.where(table.WINTERTODT == WINTERTODT)
    if COX is not None:
        sql = sql.where(table.COX == COX)
    if HARD_COX is not None:
        sql = sql.where(table.HARD_COX == HARD_COX)
    if TOB is not None:
        sql = sql.where(table.TOB == TOB)
    if HARD_TOB is not None:
        sql = sql.where(table.HARD_TOB == HARD_TOB)
    if CLUES is not None:
        sql = sql.where(table.CLUES == CLUES)
    if FALADOR_PARTY_ROOM is not None:
        sql = sql.where(table.FALADOR_PARTY_ROOM == FALADOR_PARTY_ROOM)
    if PVP_GENERIC is not None:
        sql = sql.where(table.PVP_GENERIC == PVP_GENERIC)

    sql = sql.limit(row_count).offset(row_count * (page - 1))

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data)
    return data.rows2dict()


@router.post("/V1/user-queue/start", tags=["user"])
async def post_user_queue_start(
    user_options: user_options,
    login: str = Query(..., min_length=1, max_length=12),
    token: str = Query(..., min_length=32, max_length=32),
    user_agent: str | None = Header(default=None),
) -> json:

    # if not await verify_user_agent(user_agent=user_agent):
    #     return
    user_id = await verify_token(login=login, token=token, access_level=0)
    user_options.user_id = int(user_id)
    user_options.in_queue = True

    values = user_options.dict()
    table = UserOptions
    sql = insert(table).values(values).prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)

    return {"detail": "queue started"}


@router.get("/V1/user-queue/cancel", tags=["user"])
async def get_user_queue_cancel(
    login: str = Query(..., min_length=1, max_length=12),
    token: str = Query(..., min_length=32, max_length=32),
    user_agent: str | None = Header(default=None),
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return
    user_id = await verify_token(login=login, token=token, access_level=0)
    table = UserOptions
    sql = update(table).where(table.user_id == user_id).values(in_queue=False)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    return {"detail": "queue canceled"}
