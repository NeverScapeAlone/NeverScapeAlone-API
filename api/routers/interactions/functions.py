import logging
import random

import api.database.models as models
from api.config import redis_client
from api.utilities.utils import (
    change_rating,
    create_match,
    get_match_from_ID,
    get_party_leader_from_match_ID,
    get_rating,
    post_match_to_discord,
    ratelimit,
    search_match,
    update_player_in_group,
    verify_ID,
)
from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def like(group_identifier, request, user_id):
    if group_identifier == "0":
        return
    request_id = request["like"]
    if await change_rating(request_id=request_id, user_id=user_id, is_like=True):
        logger.info(f"{user_id} liked {request_id}")


async def dislike(group_identifier, request, user_id):
    if group_identifier == "0":
        return
    request_id = request["dislike"]
    if await change_rating(request_id=request_id, user_id=user_id, is_like=False):
        logger.info(f"{user_id} disliked {request_id}")


async def kick(group_identifier, request, user_id, manager):
    if group_identifier == "0":
        return
    kick_id = request["kick"]
    if not await verify_ID(user_id=kick_id):
        return
    if kick_id == str(user_id):
        return
    kick_id = int(kick_id)
    key, m = await get_match_from_ID(group_identifier)
    if not m:
        return

    submitting_player = None
    subject_player = None
    for player in m.players:
        if player.user_id == user_id:
            submitting_player = player
        if player.user_id == kick_id:
            subject_player = player
        if (subject_player != None) & (submitting_player != None):
            break

    if (subject_player == None) or (submitting_player == None):
        return

    if submitting_player.isPartyLeader:
        await manager.disconnect_other_user(
            group_identifier=group_identifier,
            user_to_disconnect=subject_player,
        )
        return

    if subject_player.kick_list:
        if submitting_player.user_id not in subject_player.kick_list:
            subject_player.kick_list.append(submitting_player.user_id)
    else:
        subject_player.kick_list = [submitting_player.user_id]

    await update_player_in_group(
        group_identifier=group_identifier,
        player_to_update=subject_player,
    )

    group_size = len(m.players)
    kick_length = len(subject_player.kick_list)
    threshold = int(group_size / 2) + 1
    if kick_length >= threshold:
        await manager.disconnect_other_user(
            group_identifier=group_identifier,
            user_to_disconnect=subject_player,
        )
        return


async def promote(group_identifier, request, user_id, manager):
    if group_identifier == "0":
        return
    promote_id = request["promote"]
    if not await verify_ID(user_id=promote_id):
        return
    if promote_id == str(user_id):
        return
    promote_id = int(promote_id)
    key, m = await get_match_from_ID(group_identifier)
    if not m:
        return

    submitting_player = None
    subject_player = None
    for player in m.players:
        if player.user_id == user_id:
            submitting_player = player
        if player.user_id == promote_id:
            subject_player = player
        if (subject_player != None) & (submitting_player != None):
            break

    if (subject_player == None) or (submitting_player == None):
        return

    if submitting_player.isPartyLeader:
        submitting_player.isPartyLeader = False
        subject_player.isPartyLeader = True
        await update_player_in_group(
            group_identifier=group_identifier,
            player_to_update=submitting_player,
        )
        await update_player_in_group(
            group_identifier=group_identifier,
            player_to_update=subject_player,
        )
        return

    if subject_player.promote_list:
        if submitting_player.user_id not in subject_player.promote_list:
            subject_player.promote_list.append(submitting_player.user_id)
    else:
        subject_player.promote_list = [submitting_player.user_id]

    group_size = len(m.players)
    promote_length = len(subject_player.promote_list)
    threshold = int(group_size / 2) + 1
    if promote_length >= threshold:
        party_leader = await get_party_leader_from_match_ID(
            group_identifier=group_identifier
        )
        if party_leader:
            party_leader.isPartyLeader = False
            await update_player_in_group(
                group_identifier=group_identifier,
                player_to_update=party_leader,
            )

        subject_player.promote_list = None
        subject_player.isPartyLeader = True
        await update_player_in_group(
            group_identifier=group_identifier,
            player_to_update=subject_player,
        )
        return


async def location_update(
    group_identifier, request, user_id, manager, websocket, login
):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return
    logger.info(f"{login} ->> Set Location")
    location = request["location"]
    location = models.location.parse_obj(location)

    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return
    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].location = location
    await redis_client.set(name=key, value=str(m.dict()))

    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def ping_update(group_identifier, request, manager, login):
    if group_identifier == "0":
        return
    logger.info(f"{login} ->> PING")
    ping_payload = request["ping_payload"]
    ping = models.ping.parse_obj(ping_payload).dict()
    payload = {"detail": "incoming ping", "ping_data": ping}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def search_request(request, websocket, login):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    logger.info(f"{login} -> Search")
    data = await search_match(search=request["search"])
    if data is None:
        return
    logger.info(f"{login} <- Search")
    await websocket.send_json(
        {
            "detail": "search match data",
            "search_match_data": data.dict(),
        }
    )


async def quick_match(request, websocket, login):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    logger.info(f"{login} -> Quick")
    match_list = request["match_list"]

    if "RANDOM" in match_list:
        flat_keys = await redis_client.keys(f"match:*ACTIVITY=*:PRIVATE=False")
    else:
        key_chain = []
        for activity in match_list:
            keys = await redis_client.keys(f"match:*ACTIVITY={activity}:PRIVATE=False")
            if keys:
                key_chain.append(keys)
        flat_keys = [key for keys in key_chain for key in keys]

    if not flat_keys:
        return

    match = random.choice(flat_keys)
    match = match.decode("utf-8")
    start = match.find("ID=")
    end = match.find(":ACTIVITY")
    match_id = match[start + len("ID=") : end]
    await websocket.send_json(
        {
            "detail": "request join new match",
            "join": f"{match_id}",
            "passcode": "0",
        }
    )


async def create_match_request(request, websocket, user_data, login):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    logger.info(f"{login} -> Create Match")
    initial_match = await create_match(request, user_data)
    key = f"match:ID={initial_match.ID}:ACTIVITY={initial_match.activity}:PRIVATE={initial_match.isPrivate}"
    await redis_client.set(name=key, value=str(initial_match.dict()))
    await websocket.send_json(
        {
            "detail": "request join new match",
            "join": f"{initial_match.ID}",
            "passcode": f"{initial_match.group_passcode}",
        }
    )
    await post_match_to_discord(match=initial_match)


async def update_status(group_identifier, request, websocket, user_id, login, manager):
    if group_identifier == "0":
        return
    if not await ratelimit(connecting_IP=websocket.client.host):
        return

    logger.info(f"{login} ->> Set Status")
    status_val = models.status.parse_obj(request["status"])

    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return

    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].status = status_val
    await redis_client.set(name=key, value=str(m.dict()))

    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def check_connection_request(group_identifier, websocket, user_data, user_id):
    if group_identifier == "0":
        return
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return

    players = m.players
    uids = [player.user_id for player in players]

    rating = await get_rating(user_id=user_id)
    if user_id not in uids:
        p = models.player.parse_obj(user_data)
        p.rating = rating
        m.players.append(p)
        await redis_client.set(name=key, value=str(m.dict()))

    await websocket.send_json(
        {"detail": "successful connection", "match_data": m.dict()}
    )
