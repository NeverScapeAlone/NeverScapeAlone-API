import ast
import asyncio
import json
import logging
import random
import aiohttp
from typing import Tuple
import re
import traceback
import time
from asyncio.tasks import create_task
from cgitb import text
from collections import UserDict, namedtuple
from datetime import datetime, timedelta
from optparse import Option
from better_profanity import profanity
from pstats import Stats
from typing import List, Optional

import pandas as pd
from api.database import models
from api.config import DEV_MODE, DISCORD_WEBHOOK, redis_client
from api.database.database import USERDATA_ENGINE, Engine, EngineType
from api.database.models import Users, UserToken
from fastapi import APIRouter, Header, HTTPException, Query, status
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from pyparsing import Opt
from requests import request
from sqlalchemy import (
    BIGINT,
    DATETIME,
    TIMESTAMP,
    VARCHAR,
    BigInteger,
    Text,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.exc import InternalError, OperationalError
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case, text
from sqlalchemy.sql.expression import Select, delete, insert, select, update

logger = logging.getLogger(__name__)


class world_loader(BaseModel):
    world_number: int
    activity: str
    player_count: int
    p2p: int
    f2p: int
    us: int
    eu_central: int
    eu_west: int
    oceania: int


class userBanUpdate(BaseModel):
    login: str
    wdr: Optional[str]
    runewatch: Optional[str]


async def redis_decode(bytes_encoded) -> list:
    if type(bytes_encoded) == list:
        return [ast.literal_eval(element.decode("utf-8")) for element in bytes_encoded]
    return [ast.literal_eval(bytes_encoded.decode("utf-8"))]


async def verify_ID(user_id):
    user_id = str(user_id)
    if re.fullmatch("^[0-9]{0,64}", user_id):
        return True
    return False


async def post_url(route, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url=route, json=data) as resp:
            response = await resp.text()


async def clean_notes(notes: str):
    if len(notes) > 200:
        notes = notes[:200]
        notes += "..."
    notes = profanity.censor(notes)
    notes = notes.strip()
    return notes


async def post_match_to_discord(match: models.match):

    match_privacy = "Private" if match.isPrivate else "Public"
    activity = match.activity.replace("_", " ").title()
    notes = await clean_notes(match.notes)

    webhook_payload = {
        "content": f"Updated: <t:{int(time.time())}:R>",
        "embeds": [
            {
                "author": {
                    "name": f"{match.players[0].login}",
                    "icon_url": "https://i.imgur.com/dHLO8KM.png",
                },
                "title": f"{activity}",
                "description": f"Match ID: **{match.ID}**",
                "fields": [
                    {"name": "Privacy", "value": f"{match_privacy}", "inline": True},
                    {
                        "name": "Size",
                        "value": f"{match.party_members}",
                        "inline": True,
                    },
                    {
                        "name": "Accounts",
                        "value": f"{match.requirement.accounts}",
                        "inline": True,
                    },
                    {
                        "name": "Experience",
                        "value": f"{match.requirement.experience}",
                        "inline": True,
                    },
                    {
                        "name": "Split Type",
                        "value": f"{match.requirement.split_type}",
                        "inline": True,
                    },
                    {
                        "name": "Regions",
                        "value": f"{match.requirement.regions}",
                        "inline": True,
                    },
                    {
                        "name": "Notes",
                        "value": f"`{notes}`",
                        "inline": True,
                    },
                ],
            }
        ],
    }

    await post_url(route=DISCORD_WEBHOOK, data=webhook_payload)


async def get_rating(user_id):
    keys = await redis_client.keys(f"rating:{user_id}:*")
    if not keys:
        return -1
    rating_values = await redis_client.mget(keys)
    rating_list = [int(rating) for rating in rating_values]
    return int((rating_list.count(1) / len(rating_list)) * 50)


async def ratelimit(connecting_IP):
    MAX_CALLS_SECOND = 10
    """load key formats"""
    key = f"ratelimit_call:{connecting_IP}"
    manager_key = f"ratelimit_manager:{connecting_IP}"
    tally_key = f"ratelimit_tally:{connecting_IP}"

    """ load stopgate for ratelimit tally """
    tally_data = await redis_client.get(tally_key)
    if tally_data is not None:
        # logging.info(f"{connecting_IP} >| Rate: Tally Catch") # No need to print out failed rate limits tbh, just log raises.
        return False

    """ check current rate """
    data = await redis_client.get(key)
    if data is None:
        """first time in call period, start new key"""
        await redis_client.set(name=key, value=int(1), ex=1)
        return True

    if int(data) > MAX_CALLS_SECOND:
        """exceeded per second call rate, elevate to rate manager"""
        manager_data = await redis_client.get(manager_key)
        if manager_data is None:
            """no previously set manager, due to expired watch"""
            await redis_client.set(name=manager_key, value=int(2), ex=2)
            await redis_client.set(name=tally_key, value=int(1), ex=1)
            logging.info(f"{connecting_IP} >| Rate: New Manager")
            return False

        """ previously known rate manager, advance manager """
        manager_amount = int(manager_data)
        manager_amount = manager_amount * 2  # Raise difficulty
        tally_amount = int(manager_amount / 2)  # Half difficulty for tally amount

        await redis_client.set(
            name=manager_key, value=manager_amount, ex=manager_amount
        )
        await redis_client.set(name=tally_key, value=tally_amount, ex=tally_amount)
        logging.info(
            f"{connecting_IP} >| Rate: Manager {manager_amount} & Tally {tally_amount}"
        )
        return False

    value = 1 + int(data)
    await redis_client.set(name=key, value=value, xx=True, keepttl=True)
    return True


async def verify_user_agent(user_agent):
    if DEV_MODE == True:
        return True
    if not re.fullmatch("^RuneLite", user_agent[:8]):
        return False
    return True


async def is_valid_rsn(login: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{1,12}", login):
        return False
    return True


async def validate_discord(discord: str):
    discord = discord.removeprefix("@")

    if discord == ("UserName#0000" or "NULL"):
        return None

    if re.fullmatch(".*[0-9]{4}$", discord):
        if discord[-5] != "#":
            discord = discord[:-4] + "#" + discord[-4:]

    if len(discord[:-5]) >= 1 & len(discord[:-5]) <= 64:
        return discord

    return False


async def verify_token_construction(token: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{32}", token):
        return False
    return True


async def verify_discord_id(discord_id: str) -> bool:
    if discord_id == "NULL":
        return True
    if not re.fullmatch("^[\d]*", discord_id):
        return False
    return True


async def verify_headers(
    login: str, discord: str, discord_id: str, token: str, user_agent: str
) -> int:

    if not await verify_user_agent(user_agent=user_agent):
        logging.warn(f"Bad user agent {user_agent}")
        return None

    if not await verify_token_construction(token=token):
        logging.warn(f"Bad token {token}")
        return None

    if not await is_valid_rsn(login=login):
        logging.warn(f"Bad rsn {login}")
        return None

    if not await verify_discord_id(discord_id=discord_id):
        logging.warn(f"Bad discord id {discord_id}")
        return None

    discord = await validate_discord(discord=discord)

    """check redis cache"""
    rlogin = login.replace(" ", "_")
    rdiscord = "None" if discord is None else discord
    rdiscord_id = "None" if discord_id is None else discord_id
    key = f"{rlogin}:{token}:{rdiscord_id}"
    user_id = await redis_client.get(name=key)
    if user_id is not None:
        user_id = int(user_id)
        return user_id

    sql = select(UserToken)
    sql = sql.where(UserToken.token == token)
    sql = sql.where(Users.login == login)
    sql = sql.where(Users.discord == discord)
    sql = sql.where(Users.discord_id == discord_id)
    sql = sql.join(Users, UserToken.user_id == Users.user_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            request = await session.execute(sql)
            data = sqlalchemy_result(request)
            data = data.rows2dict()

    if len(data) == 0:
        user_id = await register_user_token(
            login=login, discord=discord, discord_id=discord_id, token=token
        )
        if user_id is None:
            return None
    else:
        user_id = data[0]["user_id"]

    await redis_client.set(name=key, value=user_id, ex=120)
    return user_id


async def user(user_id: int) -> str:
    """check redis cache"""
    key = f"user_alert:{user_id}"
    alerts = await redis_client.get(name=key)
    if alerts is not None:
        alerts = await redis_decode(alerts)
        return alerts[0]

    sql = select(Users)
    sql = sql.where(Users.user_id == user_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            request = await session.execute(sql)
            data = sqlalchemy_result(request)
            data = data.rows2dict()

    if len(data) == 0:
        if data is None:
            return None
    else:
        data = data[0]

    del data["timestamp"]

    await redis_client.set(name=key, value=str(data), ex=60)
    return data


async def register_user_token(
    login: str, discord: str, discord_id: str, token: str
) -> json:
    table = Users
    sql = insert(table).values(
        {"login": login, "discord": discord, "discord_id": discord_id}
    )
    sql = sql.prefix_with("ignore")

    sql_update = (
        update(table)
        .where(table.login == login)
        .values(discord=discord, discord_id=discord_id)
    )

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)
            await session.execute(sql_update)

    sql: Select = select(table).where(table.login == login)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data_get = await session.execute(sql)

    data = sqlalchemy_result(data_get).rows2dict()

    if len(data) == 0:
        return None

    user_id = data[0]["user_id"]

    table = UserToken
    values = {"token": token, "user_id": user_id}
    sql = insert(table).values(values)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)

    return user_id


async def sanitize(string: str) -> str:
    string = string.strip()
    if not string:
        return None
    string = string.upper()
    return string


async def websocket_to_user_id(websocket):
    head = websocket.headers
    login = head["Login"]  # sender unique login
    discord = head["Discord"]  # sender unique discord
    discord_id = head["Discord_ID"]  # sender unique discord id
    token = head["Token"]  # sender unique client token
    user_agent = head["user-agent"]  # sender user-agent
    time = head["Time"]  # current sender time
    print(head)

    user_id = await verify_headers(
        login=login,
        discord=discord,
        discord_id=discord_id,
        token=token,
        user_agent=user_agent,
    )
    return user_id


async def update_player_in_group(
    group_identifier: int, player_to_update: models.player
):
    key, m = await get_match_from_ID(group_identifier)
    if not m:
        return
    for idx, player in enumerate(m.players):
        if player.user_id == player_to_update.user_id:
            break
    m.players[idx] = player_to_update
    await redis_client.set(name=key, value=m.dict())


async def get_party_leader_from_match_ID(group_identifier: int) -> models.player:
    key, m = await get_match_from_ID(group_identifier)
    if not m:
        return
    for player in m.players:
        if player.isPartyLeader:
            return player
    return None


async def change_rating(request_id, user_id: int, is_like):
    # Prevent user from rating self
    if request_id == str(user_id):
        return False
    # Verify that incoming ID is of correct format
    if not await verify_ID(user_id=request_id):
        return False
    key = f"rating:{request_id}:{user_id}"
    vote = 1 if is_like else 0
    await redis_client.set(name=key, value=int(vote))
    return True


async def update_player_in_group(
    group_identifier: int, player_to_update: models.player
):
    key, m = await get_match_from_ID(group_identifier)
    if not m:
        return
    for idx, player in enumerate(m.players):
        if player.user_id == player_to_update.user_id:
            break
    m.players[idx] = player_to_update
    await redis_client.set(name=key, value=str(m.dict()))


def matchID():
    time.sleep(1 / 10**9)
    ID = hex(int(time.time() ** 2))[4:-2][::-1]
    ID = "-".join([ID[i : i + 4] for i in range(0, len(ID), 4)])
    return ID


async def get_match_from_ID(group_identifier):
    pattern = f"match:ID={group_identifier}*"
    keys = await redis_client.keys(pattern)
    if not keys:
        return None, None
    key = keys[0]
    match = await redis_client.get(key)
    data = await redis_decode(bytes_encoded=match)
    m = models.match.parse_obj(data[0])
    return key, m


async def load_redis_from_sql():

    table = Users
    sql = select(table)
    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)
    data = sqlalchemy_result(data).rows2dict()

    mapping = dict()
    for value in data:
        user_id = value["user_id"]
        key = f"user:{user_id}"
        del value["timestamp"]
        mapping[key] = str(value)
    await redis_client.mset(mapping=mapping)


async def parse_sql(
    sql, param: dict, has_return: bool, row_count: int, page: int
) -> tuple[Text, bool]:
    if isinstance(sql, Text):
        return sql
    elif isinstance(sql, str):
        has_return = True if sql.strip().lower().startswith("select") else False

        if has_return:
            # add pagination to every query
            # max number of rows = 100k
            row_count = row_count if row_count <= 100_000 else 100_000
            page = page if page >= 1 else 1
            offset = (page - 1) * row_count
            # add limit to sql
            sql = f"{sql} limit :offset, :row_count;"
            # add the param
            param["offset"] = offset
            param["row_count"] = row_count

        # parsing
        sql: Text = text(sql)
    return (sql,)


async def execute_sql(
    sql,
    param: dict = {},
    debug: bool = False,
    engine: Engine = USERDATA_ENGINE,
    row_count: int = 100_000,
    page: int = 1,
    has_return: bool = None,
    retry_attempt: int = 0,
):
    # retry breakout
    if retry_attempt >= 5:
        logger.debug({"message": "Too many retries"})
        return None

    sleep = retry_attempt * 5
    sql, has_return = await parse_sql(sql, param, has_return, row_count, page)

    try:
        async with engine.get_session() as session:
            session: AsyncSession = session
            async with session.begin():
                rows = await session.execute(sql, param)
                records = sql_cursor(rows) if has_return else None
    # OperationalError = Deadlock, InternalError = lock timeout
    except Exception as e:
        if isinstance(e, InternalError):
            e = e if debug else ""
            logger.debug(
                {"message": f"Lock, Retry Attempt: {retry_attempt}, retrying: {e}"}
            )
        elif isinstance(e, OperationalError):
            e = e if debug else ""
            logger.debug(
                {"message": f"Deadlock, Retry Attempt: {retry_attempt}, retrying {e}"}
            )
        else:
            logger.error({"message": "Unknown Error", "error": e})
            logger.error(traceback.print_exc())
            return None
        await asyncio.sleep(random.uniform(0.1, sleep))
        records = await execute_sql(
            sql,
            param,
            debug,
            engine,
            row_count,
            page,
            has_return=has_return,
            retry_attempt=retry_attempt + 1,
        )
    return records


class sql_cursor:
    def __init__(self, rows):
        self.rows: AsyncResult = rows

    def rows2dict(self):
        return self.rows.mappings().all()

    def rows2tuple(self):
        Record = namedtuple("Record", self.rows.keys())
        return [Record(*r) for r in self.rows.fetchall()]


class sqlalchemy_result:
    def __init__(self, rows):
        self.rows = [row[0] for row in rows]

    def rows2dict(self):
        return [
            {col.name: getattr(row, col.name) for col in row.__table__.columns}
            for row in self.rows
        ]

    def rows2tuple(self):
        columns = [col.name for col in self.rows[0].__table__.columns]
        Record = namedtuple("Record", columns)
        return [
            Record(*[getattr(row, col.name) for col in row.__table__.columns])
            for row in self.rows
        ]


async def batch_function(function, data, batch_size=100):
    """
    smaller transactions, can reduce locks, but individual transaction, can cause connection pool overflow
    """
    batches = []
    for i in range(0, len(data), batch_size):
        logger.debug({"batch": {f"{function.__name__}": f"{i}/{len(data)}"}})
        batch = data[i : i + batch_size]
        batches.append(batch)

    await asyncio.gather(*[create_task(function(batch)) for batch in batches])
    return
