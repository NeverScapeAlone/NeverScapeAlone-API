from datetime import datetime
from email.policy import default
from typing import Text
from numpy import integer
from sqlalchemy import (
    INTEGER,
    TIMESTAMP,
    VARCHAR,
    BigInteger,
    Column,
    ForeignKey,
    Boolean,
    Integer,
)
from sqlalchemy.dialects.mysql import TEXT, TINYINT, VARCHAR
from sqlalchemy.dialects.mysql.types import TINYTEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# generated with sqlacodegen
Base = declarative_base()
metadata = Base.metadata


class Users(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    login = Column(VARCHAR(64))
    discord = Column(VARCHAR(64))
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
