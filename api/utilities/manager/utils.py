import logging
import os
import sys

from api.config import configVars, redis_client
from api.database import models
from api.database.database import USERDATA_ENGINE
from api.utilities.mysql.utils import register_user_token, sqlalchemy_result
from api.utilities.utils import (
    is_valid_rsn,
    redis_decode,
    validate_discord,
    verify_discord_id,
    verify_plugin_version,
    verify_token_construction,
    verify_user_agent,
)
from api.database.models import Users, UserToken
from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select
from api.routers.interactions.functions import get_match_from_ID

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
