from datetime import datetime
from email.mime import base
from enum import unique

from numpy import integer
from sqlalchemy import (
    BLOB,
    DATETIME,
    INTEGER,
    SMALLINT,
    TIME,
    TIMESTAMP,
    VARCHAR,
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    column,
    text,
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

    user_id = Column(INTEGER, primary_key=True)
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


class OptionsBoss(Base):
    __tablename__ = "options_boss"
    ID = Column(INTEGER, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    abyssal_sire = Column(TINYINT)
    alchemical_hydra = Column(TINYINT)
    barrows_chests = Column(TINYINT)
    bryophyta = Column(TINYINT)
    callisto = Column(TINYINT)
    cerberus = Column(TINYINT)
    chambers_of_xeric = Column(TINYINT)
    chambers_of_xeric_challenge_mode = Column(TINYINT)
    chaos_elemental = Column(TINYINT)
    chaos_fanatic = Column(TINYINT)
    commander_zilyana = Column(TINYINT)
    corporeal_beast = Column(TINYINT)
    dagannoth_prime = Column(TINYINT)
    dagannoth_rex = Column(TINYINT)
    dagannoth_supreme = Column(TINYINT)
    crazy_archaeologist = Column(TINYINT)
    deranged_archaeologist = Column(TINYINT)
    general_graardor = Column(TINYINT)
    giant_mole = Column(TINYINT)
    grotesque_guardians = Column(TINYINT)
    hespori = Column(TINYINT)
    kalphite_queen = Column(TINYINT)
    king_black_dragon = Column(TINYINT)
    kraken = Column(TINYINT)
    kreearra = Column(TINYINT)
    kril_tsutsaroth = Column(TINYINT)
    mimic = Column(TINYINT)
    nex = Column(TINYINT)
    nightmare = Column(TINYINT)
    phosanis_nightmare = Column(TINYINT)
    obor = Column(TINYINT)
    sarachnis = Column(TINYINT)
    scorpia = Column(TINYINT)
    skotizo = Column(TINYINT)
    tempoross = Column(TINYINT)
    the_gauntlet = Column(TINYINT)
    the_corrupted_gauntlet = Column(TINYINT)
    theatre_of_blood = Column(TINYINT)
    theatre_of_blood_hard_mode = Column(TINYINT)
    thermonuclear_smoke_devil = Column(TINYINT)
    tzkal_zuk = Column(TINYINT)
    tztok_jad = Column(TINYINT)
    venenatis = Column(TINYINT)
    vetion = Column(TINYINT)
    vorkath = Column(TINYINT)
    wintertodt = Column(TINYINT)
    zalcano = Column(TINYINT)
    zulrah = Column(TINYINT)


class OptionsMinigame(Base):
    __tablename__ = "options_minigame"
    ID = Column(INTEGER, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    barbarian_assault = Column(TINYINT)
    blast_furnace = Column(TINYINT)
    burthorpe_games_room = Column(TINYINT)
    castle_wars = Column(TINYINT)
    clan_wars = Column(TINYINT)
    dagannoth_kings = Column(TINYINT)
    fishing_trawler = Column(TINYINT)
    god_wars = Column(TINYINT)
    guardians_of_the_rift = Column(TINYINT)
    last_man_standing = Column(TINYINT)
    nightmare_zone = Column(TINYINT)
    pest_control = Column(TINYINT)
    player_owned_houses = Column(TINYINT)
    rat_pits = Column(TINYINT)
    shades_of_mortton = Column(TINYINT)
    shield_of_arrav = Column(TINYINT)
    shooting_stars = Column(TINYINT)
    soul_wars = Column(TINYINT)
    theatre_of_blood = Column(TINYINT)
    tithe_farm = Column(TINYINT)
    trouble_brewing = Column(TINYINT)
    tzhaar_fight_pit = Column(TINYINT)
    volcanic_mine = Column(TINYINT)


class OptionsMisc(Base):
    __tablename__ = "options_misc"
    ID = Column(INTEGER, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    pvp_mage_bank = Column(TINYINT)
    pvp_deep_wild = Column(TINYINT)
    pvp_one_iteming = Column(TINYINT)
    pvp_multi = Column(TINYINT)
    pvp_singles = Column(TINYINT)
    pvp_rev_caves = Column(TINYINT)
    relaxing = Column(TINYINT)
    questing = Column(TINYINT)
    exploring = Column(TINYINT)
    looking_for_mentor = Column(TINYINT)
    looking_for_mentee = Column(TINYINT)
    falador_party_room = Column(TINYINT)


class OptionsSkill(Base):
    __tablename__ = "options_skill"
    ID = Column(INTEGER, primary_key=True)
    user_id = Column(
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    attack = Column(TINYINT)
    hitpoints = Column(TINYINT)
    mining = Column(TINYINT)
    strength = Column(TINYINT)
    agility = Column(TINYINT)
    smithing = Column(TINYINT)
    defence = Column(TINYINT)
    herblore = Column(TINYINT)
    fishing = Column(TINYINT)
    ranged = Column(TINYINT)
    thieving = Column(TINYINT)
    cooking = Column(TINYINT)
    prayer = Column(TINYINT)
    crafting = Column(TINYINT)
    firemaking = Column(TINYINT)
    magic = Column(TINYINT)
    fletching = Column(TINYINT)
    woodcutting = Column(TINYINT)
    runecraft = Column(TINYINT)
    slayer = Column(TINYINT)
    farming = Column(TINYINT)
    construction = Column(TINYINT)
    hunter = Column(TINYINT)
