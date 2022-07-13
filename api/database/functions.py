import asyncio
import json
import logging
import random
import re
import time
import traceback
from unicodedata import name
from api.config import redis_client
from asyncio.tasks import create_task
from collections import namedtuple
from datetime import datetime, timedelta
from dis import disco
from typing import List, Optional
from mysqlx import UpdateStatement

import pandas as pd
import requests
from api.database.database import USERDATA_ENGINE, Engine, EngineType
from api.database.models import (
    ActiveMatches,
    UserQueue,
    Users,
    UserToken,
    WorldInformation,
)
from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Text, text, or_
from sqlalchemy.exc import InternalError, OperationalError
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession
from sqlalchemy.sql import case, text
from sqlalchemy.sql.expression import delete, insert, select, update

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


async def automatic_user_queue_cleanup():
    table = UserQueue
    sql = delete(table)
    sql = sql.where(
        or_(
            table.in_queue == 0,
            table.timestamp <= datetime.utcnow() - timedelta(minutes=360),
        )
    )
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)


async def automatic_user_active_matches_cleanup():
    table = ActiveMatches
    sql = delete(table)
    sql = sql.where(table.timestamp <= datetime.utcnow() - timedelta(minutes=60))
    sql = sql.where(table.has_accepted == 0)
    sql = sql.prefix_with("ignore")

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)


async def get_wdr_bans():
    data = requests.get("https://wdrdev.github.io/banlist.json")
    json_array = json.loads(data.content)

    payload_list = []
    for json_data in json_array:
        login = "'" + json_data["CURRENT RSN"] + "'"
        wdr = "'" + json_data["Category"].replace("'", "") + "'"
        s = "(" + login + "," + wdr + ")"
        payload_list.append(s)

    sql = text(
        f"""INSERT INTO users (login, wdr) VALUES {", ".join(payload_list)} ON DUPLICATE KEY UPDATE wdr = VALUES(wdr);"""
    )

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)


async def get_runewatch_bans():
    data = requests.get("https://runewatch.com/api/v2/rsn")
    json_nested = json.loads(data.content)

    payload_list = []
    for group in json_nested:
        array_payload = json_nested[group][0]
        login = "'" + array_payload["rsn"].replace("'", "") + "'"
        runewatch = "'" + array_payload["type"].replace("'", "") + "'"
        s = "(" + login + "," + runewatch + ")"
        payload_list.append(s)

    sql = text(
        f"""INSERT INTO users (login, runewatch) VALUES {", ".join(payload_list)} ON DUPLICATE KEY UPDATE runewatch = VALUES(runewatch);"""
    )

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)


async def post_worlds():

    table = WorldInformation
    sql = select(table)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    payload = sqlalchemy_result(data).rows2dict()
    if len(payload) == 0:
        await update_world_information()
        return

    if pd.DataFrame(payload).timestamp.max() <= datetime.utcnow() - timedelta(
        minutes=30
    ):
        sql = text("TRUNCATE TABLE world_information")
        async with USERDATA_ENGINE.get_session() as session:
            session: AsyncSession = session
            async with session.begin():
                await session.execute(sql)
        await update_world_information()
    return


async def update_world_information():
    table = WorldInformation

    version = await get_runelite_version()
    world_data = await get_world_data(version)
    worlds = await world_data_conversion(world_data)
    sql = insert(table).values(worlds)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(sql)


async def get_runelite_version():
    """
    Obtains the most up to date RuneLite version
    """
    runelite_version_url = "https://static.runelite.net/bootstrap.json"
    version_data = requests.get(runelite_version_url)
    version = json.loads(version_data.text)["artifacts"][0]["diffs"][0]["name"]
    version = version.removeprefix("client-").removesuffix(".jar")
    return version


async def get_world_data(version) -> dict:
    world_data_url = f"https://api.runelite.net/runelite-{version}/worlds.js"
    world_data = requests.get(world_data_url)
    world_data = json.loads(world_data.text)
    return world_data


async def world_data_conversion(world_data):
    cleaned_worlds = list()
    for world in world_data["worlds"]:
        if "SKILL_TOTAL" in world["types"]:
            continue
        p2p = f2p = us = eu_west = eu_central = oceania = 0

        if "MEMBERS" in world["types"]:
            p2p = 1
        else:
            f2p = 1

        location = world["location"]
        if location == 0:
            us = 1
        if location == 1:
            eu_west = 1
        if location == 3:
            oceania = 1
        if location == 7:
            eu_central = 1

        world_information = world_loader(
            world_number=world["id"],
            activity=world["activity"],
            p2p=p2p,
            f2p=f2p,
            us=us,
            eu_central=eu_central,
            eu_west=eu_west,
            oceania=oceania,
            player_count=world["players"],
        )
        cleaned_worlds.append(world_information.dict())
    return cleaned_worlds


async def verify_user_agent(user_agent):
    if not re.fullmatch("^RuneLite", user_agent[:8]):
        raise HTTPException(
            status_code=202,
            detail=f"bad header",
        )
    return True


async def is_valid_rsn(login: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{1,12}", login):
        raise HTTPException(
            status_code=202,
            detail=f"bad rsn",
        )
    return True


async def validate_discord(discord: str):
    discord = discord.removeprefix("@")

    if discord == ("UserName#0000" or "NULL"):
        return None

    if re.fullmatch(".*[0-9]{4}$", discord):
        if discord[-5] != "#":
            discord = discord[:-4] + "#" + discord[-4:]

    if len(discord[:-5]) >= 1 & len(discord[:-5]) <= 32:
        return discord

    raise HTTPException(status_code=202, detail=f"bad discord")


async def verify_token_construction(token: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{32}", token):
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
    return True


async def verify_token(login: str, discord: str, token: str, access_level=0) -> int:

    if not await verify_token_construction(token=token):
        return

    if not await is_valid_rsn(login=login):
        return

    discord = await validate_discord(discord=discord)

    """check redis cache"""
    rlogin = login.replace(" ", "_")
    rdiscord = "None" if discord is None else discord
    key = f"{rlogin}:{token}:{rdiscord}"
    user_id = await redis_client.get(name=key)
    if user_id is not None:
        user_id = int(user_id)
        return user_id

    sql = select(UserToken)
    sql = sql.where(UserToken.token == token)
    sql = sql.where(Users.login == login)
    sql = sql.where(Users.discord == discord)
    sql = sql.join(Users, UserToken.user_id == Users.user_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            request = await session.execute(sql)
            data = sqlalchemy_result(request)
            data = data.rows2dict()

    if len(data) == 0:
        raise HTTPException(status_code=202, detail="registering")

    auth_level = data[0]["auth_level"]
    if access_level > auth_level:
        raise HTTPException(
            status_code=401,
            detail=f"Insufficent permissions. You cannot access this content at your auth level.",
        )

    user_id = data[0]["user_id"]

    """set redis cache"""
    await redis_client.set(name=key, value=user_id, ex=120)
    return user_id


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
