import json

from api.config import redis_client, configVars
from api.utilities.utils import (
    USERDATA_ENGINE,
    is_valid_rsn,
    sqlalchemy_result,
    get_match_from_ID,
    redis_decode,
    get_plugin_version,
    get_github_issues,
    issues_to_response,
)
import logging
from api.database.models import Users
import api.database.models as models
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, update

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/V1/discord/verify", tags=["discord"])
async def verify_discord_account(login: str, discord_id: str, token: str) -> json:

    if not await is_valid_rsn(login=login):
        return

    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return

    table = Users
    sql = select(table)
    sql = sql.where(table.login == login)
    sql = sql.where(table.discord_id == discord_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)

    data = sqlalchemy_result(data).rows2dict()

    if len(data) == 0:
        raise HTTPException(
            status_code=202,
            detail=f"no information",
        )
        return

    if len(data) > 1:
        raise HTTPException(
            status_code=202,
            detail=f"contact support",
        )
        return

    if len(data) == 1:
        if data[0]["verified"] == True:
            raise HTTPException(
                status_code=200,
                detail=f"already verified",
            )
            return

        table = Users
        sql = update(table)
        sql = sql.where(table.login == login)
        sql = sql.where(table.discord_id == discord_id)
        sql = sql.values(verified=True)

        async with USERDATA_ENGINE.get_session() as session:
            session: AsyncSession = session
            async with session.begin():
                await session.execute(sql)

        raise HTTPException(
            status_code=200,
            detail=f"verified",
        )
    return


@router.get("/V1/discord/get-active-queues", tags=["discord"])
async def get_active_queues(token: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return
    keys = await redis_client.keys("match:*False")
    if not keys:
        raise HTTPException(
            status_code=202,
            detail=f"no information",
        )
        return

    d = dict()
    for key in keys:
        key = key.decode("utf-8")
        activity = key[key.find("ACTIVITY") + len("ACTIVITY=") : key.find(":PRIVATE")]
        if activity in list(d.items()):
            d[activity] += 1
        else:
            d[activity] = 1

    response = json.dumps(d)
    response = json.loads(response)
    return response


@router.get("/V1/discord/get-active-matches", tags=["discord"])
async def get_active_matches(token: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return

    keys = await redis_client.keys("match:*")
    if not keys:
        return {"active_matches_discord": None}

    data = await redis_client.mget(keys=keys)
    if not data:
        return
    cleaned = await redis_decode(bytes_encoded=data)

    active_matches_discord = []
    for match in cleaned:
        m = models.match.parse_obj(match)
        am = models.active_match_discord.parse_obj(m.dict())
        am.player_count = len(m.players)
        active_matches_discord.append(am.dict())

    response = {"active_matches_discord": active_matches_discord}
    response = json.dumps(response)
    response = json.loads(response)
    return response


@router.post("/V1/discord/post-invites", tags=["discord"])
async def post_invites(token: str, request: Request) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
        return
    j = await request.json()
    j = json.loads(j)
    payload = j["invites"]
    for match in payload:
        am = models.active_match_discord.parse_obj(match)
        key, m = await get_match_from_ID(group_identifier=am.ID)
        if not key:
            continue
        m.discord_invite = am.discord_invite
        await redis_client.set(name=key, value=str(m.dict()))
        logger.info(f"Invite {am.discord_invite} created for {am.ID}")


@router.get("/V1/discord/delete-match", tags=["discord"])
async def delete_match(token: str, match_id: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
    key, m = await get_match_from_ID(group_identifier=match_id)
    if not key:
        return "This match does not exist."
    if await redis_client.delete(key):
        return f"{match_id} was deleted."


@router.get("/V1/discord/get-match-information", tags=["discord"])
async def delete_match(token: str, match_id: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
    key, m = await get_match_from_ID(group_identifier=match_id)
    if not key:
        return "This match does not exist."
    response = json.dumps(m.dict())
    response = json.loads(response)
    return response


@router.get("/V1/discord/whois", tags=["discord"])
async def whois(token: str, login: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
    keys = await redis_client.keys(f"user:{login}:*")
    if not keys:
        return "This user does not exist in our system, are you sure that you have entered the name exactly as seen?"
    values = await redis_client.mget(keys)
    if not values:
        return "There was an unforseen error in finding this user's discord."
    data = await redis_decode(values)
    discord_id = data[0]["discord_id"]
    if (not discord_id) or (discord_id == "NULL"):
        return "This user exists, but we do not know their discord."
    return f"{login}'s discord is <@{discord_id}>"


@router.get("/V1/discord/update-api", tags=["discord"])
async def update_api(token: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
    OLD_MATCH_VERSION = configVars.MATCH_VERSION
    plugin_version = await get_plugin_version()
    configVars.setMATCH_VERSION(match_version=plugin_version)

    d = dict()
    if OLD_MATCH_VERSION == configVars.MATCH_VERSION:
        d["detail"] = f"API already updated to {configVars.MATCH_VERSION}"
    else:
        d[
            "detail"
        ] = f"API updated to {configVars.MATCH_VERSION} from {OLD_MATCH_VERSION}"

    response = json.dumps(d)
    response = json.loads(response)
    return response


@router.get("/V1/discord/get-tasks", tags=["discord"])
async def update_api(token: str) -> json:
    if token != configVars.DISCORD_TOKEN:
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )

    data = await get_github_issues()
    d = await issues_to_response(data)

    payload = dict()
    payload["issues"] = d

    response = json.dumps(payload)
    response = json.loads(response)
    return response
