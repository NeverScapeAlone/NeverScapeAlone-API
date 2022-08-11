import json
import logging
import random
import sys
import time
from ast import Delete
from cmath import log
from cProfile import run
from dataclasses import replace
from datetime import datetime
from email.policy import default
from multiprocessing.sharedctypes import Value
from re import L, sub
from tokenize import group
from typing import List, Optional, Text
from urllib.request import Request
from xmlrpc.client import Boolean, boolean

import networkx as nx
import numpy as np
import pandas as pd
from certifi import where
from fastapi.responses import HTMLResponse
from h11 import ConnectionClosed, InformationalResponse
from pydantic import BaseModel
from pyparsing import Opt
from sqlalchemy import (
    INTEGER,
    TEXT,
    TIMESTAMP,
    VARCHAR,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    Boolean,
)
from sqlalchemy.dialects.mysql import TEXT, TINYINT, VARCHAR, Insert
from sqlalchemy.dialects.mysql.types import TINYTEXT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import aliased, relationship
from sqlalchemy.sql import case, text
from sqlalchemy.sql.expression import Select, insert, select, update
from urllib3 import HTTPResponse

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


class UserRatingHistory(Base):
    __tablename__ = "user_rating_history"
    ID = Column(BigInteger, primary_key=True)
    timestamp = Column(TIMESTAMP)
    s_user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    r_user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    rating = Column(TINYINT)
    comment = Column(TINYTEXT)
    request_history_id = Column(BigInteger)


class UserToken(Base):
    __tablename__ = "user_token"
    ID = Column(INTEGER, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    auth_level = Column(TINYINT)
    token = Column(TINYTEXT)


class UserPoints(Base):
    __tablename__ = "user_points"
    ID = Column(BigInteger, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    points = Column(BigInteger)


class ActiveMatches(Base):
    __tablename__ = "active_matches"
    ID = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    party_identifier = Column(TINYTEXT)
    user_queue_ID = Column(Integer)
    activity = Column(TEXT)
    party_member_count = Column(Integer)
    has_accepted = Column(Boolean, default=False)
    discord_invite = Column(TEXT, default=None)
    timestamp = Column(TIMESTAMP)


class UserQueue(Base):
    __tablename__ = "user_queue"
    ID = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    timestamp = Column(TIMESTAMP)
    in_queue = Column(Boolean, unique=False, default=False)
    activity = Column(TINYTEXT)
    party_member_count = Column(Integer)
    self_experience_level = Column(Integer)
    partner_experience_level = Column(Integer)
    us = Column(Boolean, unique=False, default=False)
    eu_central = Column(Boolean, unique=False, default=False)
    eu_west = Column(Boolean, unique=False, default=False)
    oceania = Column(Boolean, unique=False, default=False)
    f2p = Column(Boolean, unique=False, default=False)
    p2p = Column(Boolean, unique=False, default=False)


class WorldInformation(Base):
    __tablename__ = "world_information"
    ID = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP)
    world_number = Column(Integer)
    activity = Column(TEXT)
    us = Column(Boolean, unique=False, default=False)
    eu_central = Column(Boolean, unique=False, default=False)
    eu_west = Column(Boolean, unique=False, default=False)
    oceania = Column(Boolean, unique=False, default=False)
    f2p = Column(Boolean, unique=False, default=False)
    p2p = Column(Boolean, unique=False, default=False)
    player_count = Column(Integer)


class search_match_info(BaseModel):
    ID: str
    activity: str
    party_members: str
    isPrivate: bool
    experience: str
    split_type: str
    accounts: str
    regions: str
    player_count: str
    party_leader: str
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


class all_search_match_info(BaseModel):
    search_matches: List[search_match_info]


class stats(BaseModel):
    """player skills"""

    attack: int
    strength: int
    defense: int
    ranged: int
    prayer: int
    magic: int
    runecraft: int
    construction: int
    hitpoints: int
    agility: int
    herblore: int
    thieving: int
    crafting: int
    fletching: int
    slayer: int
    hunter: int
    mining: int
    smithing: int
    fishing: int
    cooking: int
    firemaking: int
    woodcutting: int
    farming: int


class status(BaseModel):
    """player status"""

    hp: int
    base_hp: int
    prayer: int
    base_prayer: int
    run_energy: int


class player(BaseModel):
    """player model"""

    discord: str
    stats: Optional[stats]
    status: Optional[status]
    location: Optional[location]
    runewatch: Optional[str]
    wdr: Optional[str]
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
