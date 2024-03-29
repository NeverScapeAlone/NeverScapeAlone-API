from ctypes.wintypes import PINT
from typing import List, Optional
from xmlrpc.client import Boolean

from pydantic import BaseModel
from sqlalchemy import (
    INTEGER,
    TEXT,
    TIMESTAMP,
    VARCHAR,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.mysql import TEXT, TINYINT, VARCHAR
from sqlalchemy.dialects.mysql.types import TINYTEXT
from sqlalchemy.ext.declarative import declarative_base

# generated with sqlacodegen
Base = declarative_base()
metadata = Base.metadata


class Users(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    login = Column(VARCHAR(64))
    discord = Column(VARCHAR(64))
    discord_id = Column(TEXT)
    verified = Column(Boolean, default=False)
    runewatch = Column(TEXT)
    wdr = Column(TEXT)
    timestamp = Column(TIMESTAMP)


class UserToken(Base):
    __tablename__ = "user_token"
    ID = Column(INTEGER, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    auth_level = Column(TINYINT)
    token = Column(TINYTEXT)


class AccessTokens(Base):
    __tablename__ = "access_tokens"
    ID = Column(Integer, primary_key=True)
    access_token = Column(TIMESTAMP)
    permissions = Column(Integer)


class search_match_info(BaseModel):
    ID: str
    activity: str
    party_members: str
    isPrivate: bool
    RuneGuard: bool
    experience: str
    split_type: str
    accounts: str
    regions: str
    player_count: str
    party_leader: str
    match_version: str
    notes: Optional[str]


class location(BaseModel):
    """location model"""

    x: int
    y: int
    regionX: int
    regionY: int
    regionID: int
    plane: int
    world: int


class equipment_item(BaseModel):
    item_id: int
    item_amount: Optional[int]


class equipment(BaseModel):
    head: Optional[equipment_item]
    cape: Optional[equipment_item]
    amulet: Optional[equipment_item]
    ammo: Optional[equipment_item]
    weapon: Optional[equipment_item]
    body: Optional[equipment_item]
    shield: Optional[equipment_item]
    legs: Optional[equipment_item]
    gloves: Optional[equipment_item]
    boots: Optional[equipment_item]
    ring: Optional[equipment_item]


class inventory_item(BaseModel):
    """inventory_item model"""

    item_id: int
    item_amount: int


class prayer_slot(BaseModel):
    """prayer slot"""

    prayer_name: str
    prayer_varbit: int


class all_search_match_info(BaseModel):
    search_matches: List[search_match_info]


class stat_information(BaseModel):
    boosted: int
    real: int
    experience: int


class stats(BaseModel):
    """player skills"""

    Attack: stat_information
    Strength: stat_information
    Defence: stat_information
    Ranged: stat_information
    Prayer: stat_information
    Magic: stat_information
    Runecraft: stat_information
    Construction: stat_information
    Hitpoints: stat_information
    Agility: stat_information
    Herblore: stat_information
    Thieving: stat_information
    Crafting: stat_information
    Fletching: stat_information
    Slayer: stat_information
    Hunter: stat_information
    Mining: stat_information
    Smithing: stat_information
    Fishing: stat_information
    Cooking: stat_information
    Firemaking: stat_information
    Woodcutting: stat_information
    Farming: stat_information
    Overall: stat_information


class status(BaseModel):
    """player status"""

    hp: int
    base_hp: int
    prayer: int
    base_prayer: int
    run_energy: int
    special_attack: int


class player(BaseModel):
    """player model"""

    discord: str
    stats: Optional[stats]
    status: Optional[status]
    location: Optional[location]
    inventory: Optional[list[inventory_item]]
    prayer: Optional[list[prayer_slot]]
    equipment: Optional[equipment]
    runewatch: Optional[str]
    wdr: Optional[str]
    gamestate: Optional[int]
    verified: Optional[bool]
    rating: Optional[int]
    kick_list: Optional[list[int]]
    promote_list: Optional[list[int]]
    user_id: int
    login: str
    isPartyLeader: Optional[bool] = False


class requirement(BaseModel):
    """match requirements"""

    experience: str
    split_type: str
    accounts: str
    regions: str


class active_match_discord(BaseModel):
    """active match model"""

    discord_invite: Optional[str]
    player_count: Optional[int]
    ID: str


class match(BaseModel):
    """match model"""

    discord_invite: Optional[str]
    ID: str
    activity: str
    party_members: str
    group_passcode: str
    isPrivate: bool
    RuneGuard: bool
    match_version: str
    notes: Optional[str]
    ban_list: Optional[list[int]]
    requirement: requirement
    players: list[player]


class ping(BaseModel):
    """ping model"""

    username: str
    x: int
    y: int
    regionX: int
    regionY: int
    regionID: int
    plane: int
    color_r: int
    color_g: int
    color_b: int
    color_alpha: int
    isAlert: bool


class chat(BaseModel):
    """chat model"""

    username: Optional[str]
    message: str
    timestamp: Optional[int]


class create_match(BaseModel):
    """create match payload"""

    activity: str
    party_members: str
    experience: str
    split_type: str
    accounts: str
    regions: str
    RuneGuard: str
    notes: str
    group_passcode: str


class request(BaseModel):
    """incoming request model from the client"""

    detail: str
    chat_message: Optional[chat]
    like: Optional[int]
    dislike: Optional[int]
    kick: Optional[int]
    promote: Optional[int]
    status: Optional[status]
    location: Optional[location]
    inventory: Optional[List[inventory_item]]
    stats: Optional[stats]
    prayer: Optional[List[prayer_slot]]
    equipment: Optional[equipment]
    ping_payload: Optional[ping]
    search: Optional[str]
    match_list: Optional[List[str]]
    gamestate: Optional[int]
    create_match: Optional[create_match]
