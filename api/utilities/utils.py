import ast
import asyncio
import hashlib
import json
import logging
import random
import re
import time
import traceback
import requests
import pandas as pd
import string
from asyncio.tasks import create_task
from cgitb import text
from collections import namedtuple
from typing import Optional

import aiohttp
from api.config import configVars, redis_client
from api.database import models
from api.database.database import USERDATA_ENGINE, Engine
from api.utilities.wordkey import WordKey
from api.database.models import AccessTokens, Users, UserToken
from better_profanity import profanity
from bs4 import BeautifulSoup
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from sqlalchemy import Text, select, text
from sqlalchemy.exc import InternalError, OperationalError
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.sql.expression import Select, insert, select, update

logger = logging.getLogger(__name__)
wordkey = WordKey()


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


async def clean_text(notes: str):
    if len(notes) > 200:
        notes = notes[:200]
        notes += "..."
    notes = profanity.censor(notes)
    notes = re.sub("<[^>]*>", "", notes)
    notes = notes.strip()
    return notes


async def post_match_to_discord(match: models.match):

    match_privacy = "Private" if match.isPrivate else "Public"
    activity = match.activity.replace("_", " ").title()
    notes = await clean_text(match.notes)

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

    # await post_url(route=configVars.DISCORD_WEBHOOK, data=webhook_payload)


async def get_rating(user_id):
    keys = await redis_client.keys(f"rating:{user_id}:*")
    if not keys:
        return -1
    rating_values = await redis_client.mget(keys)
    rating_list = [int(rating) for rating in rating_values]
    if len(rating_list) <= 10:
        return -1
    return int((rating_list.count(1) / len(rating_list)) * 50)


def sha256(string: str) -> str:
    """sha256 encodes a string"""
    return hashlib.sha256(string.encode()).hexdigest()


async def ratelimit(connecting_IP):
    MAX_CALLS_SECOND = 10
    """load key formats"""
    key = sha256(string=f"ratelimit_call:{connecting_IP}")
    manager_key = sha256(string=f"ratelimit_manager:{connecting_IP}")
    tally_key = sha256(string=f"ratelimit_tally:{connecting_IP}")

    """ load stopgate for ratelimit tally """
    tally_data = await redis_client.get(tally_key)
    if tally_data is not None:
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
            return False

        """ previously known rate manager, advance manager """
        manager_amount = int(manager_data)
        manager_amount = manager_amount * 2  # Raise difficulty
        tally_amount = int(manager_amount / 2)  # Half difficulty for tally amount

        await redis_client.set(
            name=manager_key, value=manager_amount, ex=manager_amount
        )
        await redis_client.set(name=tally_key, value=tally_amount, ex=tally_amount)
        return False

    value = 1 + int(data)
    await redis_client.set(name=key, value=value, xx=True, keepttl=True)
    return True


async def get_plugin_version():
    """gets the most up-to-date NeverScapeAlone plugin version"""
    url = (
        "https://github.com/NeverScapeAlone/never-scape-alone/blob/master/build.gradle"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as resp:
            response = await resp.text()
    soup = BeautifulSoup(response, "html.parser")
    for s in soup.find_all(id=re.compile("^LC[0-9]")):
        if not s.find_all(string=re.compile("^version")):
            continue
        s = "".join(s.stripped_strings)
        match = re.match("^version[ ]{0,1}=[ ]{0,1}", s)
        if not match:
            continue
        version = s[match.span()[1] :].strip("'")
    return version


async def verify_user_agent(user_agent):
    if not re.fullmatch("^RuneLite", user_agent[:8]):
        return False
    return True


async def verify_plugin_version(plugin_version):
    if configVars.MATCH_VERSION[:2] == plugin_version[:2]:
        return True
    return False


async def is_valid_rsn(login: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{1,12}", login):
        return False
    return True


async def validate_discord(discord: str):
    if re.fullmatch(
        "^(?:[A-Za-z\d+/]{4})*(?:[A-Za-z\d+/]{3}=|[A-Za-z\d+/]{2}==)?$", discord
    ):
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


async def socket_userID(websocket: WebSocket) -> int:

    login = websocket.headers["Login"]
    discord = websocket.headers["Discord"]
    discord_id = websocket.headers["Discord_ID"]
    token = websocket.headers["Token"]
    user_agent = websocket.headers["User-Agent"]
    plugin_version = websocket.headers["Version"]

    if not await verify_plugin_version(plugin_version=plugin_version):
        logging.warn(
            f"Old plugin version {plugin_version}, current: {configVars.MATCH_VERSION}"
        )
        return "E:Outdated Plugin"

    if not await verify_user_agent(user_agent=user_agent):
        logging.warn(f"Bad user agent {user_agent}")
        return "E:Bad User-Agent"

    if not await verify_token_construction(token=token):
        logging.warn(f"Bad token {token}")
        return "E:Bad Token"

    if not await is_valid_rsn(login=login):
        logging.warn(f"Bad rsn {login}")
        return "E:Invalid RSN"

    if not await verify_discord_id(discord_id=discord_id):
        logging.warn(f"Bad discord id {discord_id}")
        return "E:Bad Discord ID"

    discord = await validate_discord(discord=discord)

    """check redis cache"""
    rlogin = login.replace(" ", "_")
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

    if not data:
        user_id = await register_user_token(
            login=login, discord=discord, discord_id=discord_id, token=token
        )
        if user_id is None:
            return None
    else:
        user_id = data[0]["user_id"]

    await redis_client.set(name=key, value=user_id, ex=120)
    return user_id


async def validate_access_token(access_token: str):
    sql = select(AccessTokens)
    sql = sql.where(AccessTokens.access_token == access_token)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            request = await session.execute(sql)
            data = sqlalchemy_result(request)
            data = data.rows2dict()

    return data


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

    if not data:
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


def encode(num):
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    if num == 0:
        return alphabet[0]
    arr = []
    arr_append = arr.append
    _divmod = divmod
    base = len(alphabet)
    while num:
        num, rem = _divmod(num, base)
        arr_append(alphabet[rem])
    arr.reverse()
    return "".join(arr)


def matchID():
    ID = encode(time.time_ns())[3:][::-1]
    splits = [wordkey.key[ID[i : i + 2]] for i in range(0, len(ID), 2)]
    ID = "-".join(splits)
    return ID


async def get_match_from_ID(group_identifier):
    pattern = f"match:ID={group_identifier}*"
    keys = await redis_client.keys(pattern)
    if not keys:
        return None, None
    key = keys[0]
    match = await redis_client.get(key)
    if not match:
        return None, None
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
        login = value["login"]
        key = f"user:{login}:{user_id}"
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


async def get_wdr_bans():
    data = requests.get("https://wdrdev.github.io/banlist.json")
    json_array = json.loads(data.content)

    payload_list = []
    for json_data in json_array:
        login = "'" + json_data["CURRENT RSN"] + "'"
        wdr = "'" + json_data["Category"].replace("'", "") + "'"
        s = "(" + login + "," + wdr + ")"
        payload_list.append(s)

    null_query = text(f"""UPDATE users SET runewatch = null WHERE 1=1""")
    insert_query = text(
        f"""INSERT INTO users (login, wdr) VALUES {", ".join(payload_list)} ON DUPLICATE KEY UPDATE wdr = VALUES(wdr);"""
    )

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(null_query)
            await session.execute(insert_query)


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

    null_query = text(f"""UPDATE users SET runewatch = null WHERE 1=1""")
    insert_query = text(
        f"""INSERT INTO users (login, runewatch) VALUES {", ".join(payload_list)} ON DUPLICATE KEY UPDATE runewatch = VALUES(runewatch);"""
    )
    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(null_query)
            await session.execute(insert_query)


async def search_match(search: str):
    if re.fullmatch("^[a-z]{2,7}-[a-z]{2,7}-[a-z]{2,7}", search):
        keys = await redis_client.keys(f"match:ID={search}*")
    else:
        search = await sanitize(search)
        keys = await redis_client.keys(f"match:*ACTIVITY={search}*")
    keys = keys[:50]
    values = await redis_client.mget(keys)
    if not values:
        return None
    match_data = await redis_decode(values)

    search_matches = []
    for match in match_data:
        requirement = match["requirement"]

        party_leader = "NO LEADER"
        for player in match["players"]:
            if player["isPartyLeader"] != True:
                continue
            party_leader = player["login"]

        val = models.search_match_info(
            ID=str(match["ID"]),
            activity=match["activity"],
            notes=match["notes"],
            party_members=match["party_members"],
            isPrivate=match["isPrivate"],
            RuneGuard=match["RuneGuard"],
            experience=requirement["experience"],
            split_type=requirement["split_type"],
            accounts=requirement["accounts"],
            regions=requirement["regions"],
            player_count=str(len(match["players"])),
            match_version=match["match_version"],
            party_leader=party_leader,
        )
        search_matches.append(val)
    data = models.all_search_match_info(search_matches=search_matches)
    return data


async def create_match(request, user_data):
    discord = user_data["discord"]
    user_id = user_data["user_id"]
    verified = user_data["verified"]
    runewatch = user_data["runewatch"]
    wdr = user_data["wdr"]
    login = user_data["login"]

    sub_payload = request["create_match"]
    activity = sub_payload["activity"]
    party_members = sub_payload["party_members"]
    experience = sub_payload["experience"]
    split_type = sub_payload["split_type"]
    accounts = sub_payload["accounts"]
    regions = sub_payload["regions"]
    RuneGuard = sub_payload["RuneGuard"]
    notes = await clean_text(sub_payload["notes"])
    group_passcode = sub_payload["group_passcode"]
    private = bool(group_passcode)
    ID = matchID()
    match_version = configVars.MATCH_VERSION

    rating = await get_rating(user_id=user_id)

    initial_match = models.match(
        ID=ID,
        activity=activity,
        party_members=party_members,
        isPrivate=private,
        notes=notes,
        group_passcode=group_passcode,
        RuneGuard=RuneGuard,
        match_version=match_version,
        requirement=models.requirement(
            experience=experience,
            split_type=split_type,
            accounts=accounts,
            regions=regions,
        ),
        players=[
            # the first player to be added to the group
            models.player(
                discord="NONE" if discord is None else discord,
                isPartyLeader=True,
                verified=verified,
                user_id=user_id,
                login=login,
                rating=rating,
                runewatch=runewatch,
                wdr=wdr,
            )
        ],
    )
    return initial_match


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


class PandasCursor:
    def __init__(self, rows):
        self.rows: AsyncResult = rows

    def __get_values(self):
        return self.rows.fetchall()

    def __get_columns(self):
        return self.rows.keys()

    def df(self):
        values = self.__get_values()
        columns = self.__get_columns()
        df = pd.DataFrame(columns=columns)
        df = df.append(values)
        return df


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


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


async def get_github_issues(per_page=100):
    url = f"https://api.github.com/repos/neverscapealone/never-scape-alone/issues?per_page={per_page}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response = await resp.json()
    return response


async def issues_to_response(data) -> list:
    payload = list()
    for issue_dict in data:
        d = dict()
        issue = AttrDict(issue_dict)
        points = 0
        for label in issue.labels:
            label_name = label["name"]
            count = label_name[: label_name.find("-")]
            points += int(count)
        l = [(issue.title, issue.url), points]
        payload.append(l)
    sorted_payload = sorted(payload, reverse=True, key=lambda x: x[1])

    response = list()
    for title, points in sorted_payload:
        d = dict()
        d["title"] = title[0]
        d["url"] = title[1]
        d["priority"] = points
        response.append(d)
    return response


async def automatic_match_cleanup(manager):
    """cleans up headless and ghost matches automatically
    headless matches: matches with no manager class, but there is data of the match
    ghost matches: there is no data for this match, but it exists in the manager class.
    """

    async def get_matches_with_data():
        """gets matches with data, doesn't necessairly mean these matches have a manager attached to them"""
        keys = await redis_client.keys("match:*")
        if not keys:
            return list()
        data = await redis_client.mget(keys=keys)
        if not data:
            return list()
        cleaned = await redis_decode(bytes_encoded=data)
        ids = []
        for match in cleaned:
            m = models.match.parse_obj(match)
            ids.append(m.ID)
        return ids

    async def get_managed_matches(manager=manager):
        return list(manager.active_connections.keys())

    data_matches = await get_matches_with_data()
    managed_matches = await get_managed_matches()
    headless = [ID for ID in data_matches if ID not in managed_matches]
    ghosts = [ID for ID in managed_matches if ID not in data_matches if ID != "0"]

    for h in headless:
        key, m = await get_match_from_ID(h)
        await redis_client.delete(key)
        logger.info(f"Headless {h} deleted.")

    for g in ghosts:
        del manager.active_connections[g]
        logger.info(f"Ghost {g} deleted.")
