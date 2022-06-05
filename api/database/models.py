from datetime import datetime
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


class RequestHistory(Base):
    __tablename__ = "request_history"
    ID = Column(BigInteger, primary_key=True)

    s_user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    r_user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    timestamp_START = Column(TIMESTAMP)
    timestamp_DEAD = Column(TIMESTAMP)
    status = Column(TINYINT)


class UserOptions(Base):
    __tablename__ = "user_options"
    ID = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    timestamp = Column(TIMESTAMP)
    in_queue = Column(Boolean, unique=False, default=False)
    ATTACK = Column(Boolean, unique=False, default=False)
    STRENGTH = Column(Boolean, unique=False, default=False)
    DEFENCE = Column(Boolean, unique=False, default=False)
    HITPOINTS = Column(Boolean, unique=False, default=False)
    RANGED = Column(Boolean, unique=False, default=False)
    PRAYER = Column(Boolean, unique=False, default=False)
    MAGIC = Column(Boolean, unique=False, default=False)
    COOKING = Column(Boolean, unique=False, default=False)
    WOODCUTTING = Column(Boolean, unique=False, default=False)
    FLETCHING = Column(Boolean, unique=False, default=False)
    FISHING = Column(Boolean, unique=False, default=False)
    FIREMAKING = Column(Boolean, unique=False, default=False)
    CRAFTING = Column(Boolean, unique=False, default=False)
    SMITHING = Column(Boolean, unique=False, default=False)
    MINING = Column(Boolean, unique=False, default=False)
    HERBLORE = Column(Boolean, unique=False, default=False)
    AGILITY = Column(Boolean, unique=False, default=False)
    THIEVING = Column(Boolean, unique=False, default=False)
    SLAYER = Column(Boolean, unique=False, default=False)
    FARMING = Column(Boolean, unique=False, default=False)
    RUNECRAFT = Column(Boolean, unique=False, default=False)
    HUNTER = Column(Boolean, unique=False, default=False)
    CONSTRUCTION = Column(Boolean, unique=False, default=False)
    ALL_SKILLS = Column(Boolean, unique=False, default=False)
    ABYSSAL_SIRE = Column(Boolean, unique=False, default=False)
    ALCHEMICAL_HYDRA = Column(Boolean, unique=False, default=False)
    BRYOPHYTA = Column(Boolean, unique=False, default=False)
    CERBERUS = Column(Boolean, unique=False, default=False)
    GROTESQUE_GUARDIANS = Column(Boolean, unique=False, default=False)
    HESPORI = Column(Boolean, unique=False, default=False)
    KRAKEN = Column(Boolean, unique=False, default=False)
    MIMIC = Column(Boolean, unique=False, default=False)
    OBOR = Column(Boolean, unique=False, default=False)
    PHOSANIS_NIGHTMARE = Column(Boolean, unique=False, default=False)
    SKOTIZO = Column(Boolean, unique=False, default=False)
    GAUNTLET = Column(Boolean, unique=False, default=False)
    GAUNTLET_CORRUPTED = Column(Boolean, unique=False, default=False)
    THERMONUCLEARSMOKEDEVIL = Column(Boolean, unique=False, default=False)
    TZ_KAL_ZUK = Column(Boolean, unique=False, default=False)
    TZ_TOK_JAD = Column(Boolean, unique=False, default=False)
    VORKATH = Column(Boolean, unique=False, default=False)
    ZULRAH = Column(Boolean, unique=False, default=False)
    BARROWS = Column(Boolean, unique=False, default=False)
    CALLISTO = Column(Boolean, unique=False, default=False)
    CHAOS_ELEMENTAL = Column(Boolean, unique=False, default=False)
    CHAOS_FANATIC = Column(Boolean, unique=False, default=False)
    COMMANDER_ZILYANA = Column(Boolean, unique=False, default=False)
    CORPOREAL_BEAST = Column(Boolean, unique=False, default=False)
    ARCHAEOLOGIST_CRAZY = Column(Boolean, unique=False, default=False)
    ARCHAEOLOGIST_DERANGED = Column(Boolean, unique=False, default=False)
    DAGANNOTH_PRIME = Column(Boolean, unique=False, default=False)
    DAGANNOTH_REX = Column(Boolean, unique=False, default=False)
    DAGANNOTH_SUPREME = Column(Boolean, unique=False, default=False)
    GENERAL_GRAARDOR = Column(Boolean, unique=False, default=False)
    GIANT_MOLE = Column(Boolean, unique=False, default=False)
    KALPHITE_QUEEN = Column(Boolean, unique=False, default=False)
    KING_BLACK_DRAGON = Column(Boolean, unique=False, default=False)
    KREEARRA = Column(Boolean, unique=False, default=False)
    KRIL_TSUTSAROTH = Column(Boolean, unique=False, default=False)
    NEX = Column(Boolean, unique=False, default=False)
    NIGHTMARE = Column(Boolean, unique=False, default=False)
    SARACHNIS = Column(Boolean, unique=False, default=False)
    SCORPIA = Column(Boolean, unique=False, default=False)
    VENENATIS = Column(Boolean, unique=False, default=False)
    VETION = Column(Boolean, unique=False, default=False)
    ZALCANO = Column(Boolean, unique=False, default=False)
    BARBARIAN_ASSAULT = Column(Boolean, unique=False, default=False)
    BLAST_FURNACE = Column(Boolean, unique=False, default=False)
    BLAST_MINE = Column(Boolean, unique=False, default=False)
    BRIMHAVEN_AGILITY_ARENA = Column(Boolean, unique=False, default=False)
    BOUNTY_HUNTER_HUNTER = Column(Boolean, unique=False, default=False)
    BOUNTY_HUNTER_ROGUE = Column(Boolean, unique=False, default=False)
    CAMDOZAAL_VAULT = Column(Boolean, unique=False, default=False)
    CASTLE_WARS = Column(Boolean, unique=False, default=False)
    CLAN_WARS = Column(Boolean, unique=False, default=False)
    CREATURE_CREATION = Column(Boolean, unique=False, default=False)
    DUEL_ARENA = Column(Boolean, unique=False, default=False)
    FISHING_TRAWLER = Column(Boolean, unique=False, default=False)
    GNOME_BALL = Column(Boolean, unique=False, default=False)
    GNOME_RESTAURANT = Column(Boolean, unique=False, default=False)
    GUARDIANS_OF_THE_RIFT = Column(Boolean, unique=False, default=False)
    HALLOWED_SEPULCHRE = Column(Boolean, unique=False, default=False)
    PURO_PURO = Column(Boolean, unique=False, default=False)
    MAGE_ARENA = Column(Boolean, unique=False, default=False)
    MAHOGANY_HOMES = Column(Boolean, unique=False, default=False)
    MAGE_TRAINING_ARENA = Column(Boolean, unique=False, default=False)
    NIGHTMARE_ZONE = Column(Boolean, unique=False, default=False)
    ORGANIZED_CRIME = Column(Boolean, unique=False, default=False)
    PEST_CONTROL = Column(Boolean, unique=False, default=False)
    PYRAMID_PLUNDER = Column(Boolean, unique=False, default=False)
    ROGUES_DEN = Column(Boolean, unique=False, default=False)
    SHADES_OF_MORTON = Column(Boolean, unique=False, default=False)
    SORCERESS_GARDEN = Column(Boolean, unique=False, default=False)
    TAI_BWO_WANNAI = Column(Boolean, unique=False, default=False)
    TITHE_FARM = Column(Boolean, unique=False, default=False)
    TROUBLE_BREWING = Column(Boolean, unique=False, default=False)
    UNDERWATER_AGILITY_AND_THIEVING = Column(Boolean, unique=False, default=False)
    VOLCANIC_MINE = Column(Boolean, unique=False, default=False)
    LAST_MAN_STANDING = Column(Boolean, unique=False, default=False)
    SOUL_WARS = Column(Boolean, unique=False, default=False)
    TEMPOROSS = Column(Boolean, unique=False, default=False)
    WINTERTODT = Column(Boolean, unique=False, default=False)
    COX = Column(Boolean, unique=False, default=False)
    HARD_COX = Column(Boolean, unique=False, default=False)
    TOB = Column(Boolean, unique=False, default=False)
    HARD_TOB = Column(Boolean, unique=False, default=False)
    CLUES = Column(Boolean, unique=False, default=False)
    FALADOR_PARTY_ROOM = Column(Boolean, unique=False, default=False)
    PVP_GENERIC = Column(Boolean, unique=False, default=False)
