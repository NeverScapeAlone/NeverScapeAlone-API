import logging
import random
import re
import time

import api.database.models as models
from api.config import configVars, redis_client
from api.database import models
from api.utilities.activities import ActivityReference
from api.utilities.ratelimiter.utils import ratelimit
from api.utilities.utils import (
    clean_text,
    matchID,
    post_url,
    redis_decode,
    sanitize,
    verify_ID,
)

logger = logging.getLogger(__name__)
activityReference = ActivityReference()


async def like(group_identifier, request: models.request, user_id, manager):
    if group_identifier == "0":
        return
    request_id = request.like
    if await change_rating(request_id=request_id, user_id=user_id, is_like=True):
        sub_payload = dict()
        sub_payload["liker"] = user_id
        sub_payload["liked"] = request_id
        payload = dict()
        payload["like"] = sub_payload
        await manager.match_writer(
            group_identifier=group_identifier, dictionary=payload
        )


async def dislike(group_identifier, request: models.request, user_id, manager):
    if group_identifier == "0":
        return
    request_id = request.dislike
    if await change_rating(request_id=request_id, user_id=user_id, is_like=False):
        sub_payload = dict()
        sub_payload["disliker"] = user_id
        sub_payload["disliked"] = request_id
        payload = dict()
        payload["dislike"] = sub_payload
        await manager.match_writer(
            group_identifier=group_identifier, dictionary=payload
        )


async def kick(group_identifier, request: models.request, user_id, manager):
    if group_identifier == "0":
        return
    kick_id = request.kick
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

    sub_payload = dict()
    sub_payload["submitting_player"] = submitting_player.login
    sub_payload["subject_player"] = subject_player.login
    payload = dict()
    payload["kick_request"] = sub_payload
    await manager.match_writer(group_identifier=group_identifier, dictionary=payload)

    if (subject_player == None) or (submitting_player == None):
        return

    if submitting_player.isPartyLeader:
        sub_payload = dict()
        sub_payload["submitting_player"] = submitting_player.login
        sub_payload["subject_player"] = subject_player.login
        payload = dict()
        payload["kicked"] = sub_payload
        await manager.match_writer(
            group_identifier=group_identifier, dictionary=payload
        )
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
        sub_payload = dict()
        sub_payload["submitting_player"] = submitting_player.login
        sub_payload["subject_player"] = subject_player.login
        payload = dict()
        payload["kicked"] = sub_payload
        await manager.match_writer(
            group_identifier=group_identifier, dictionary=payload
        )
        await manager.disconnect_other_user(
            group_identifier=group_identifier,
            user_to_disconnect=subject_player,
        )
        return


async def promote(group_identifier, request: models.request, user_id, manager):
    if group_identifier == "0":
        return
    promote_id = request.promote
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

    sub_payload = dict()
    sub_payload["submitting_player"] = submitting_player.login
    sub_payload["subject_player"] = subject_player.login
    payload = dict()
    payload["promote_request"] = sub_payload
    await manager.match_writer(group_identifier=group_identifier, dictionary=payload)

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
        sub_payload = dict()
        sub_payload["submitting_player"] = submitting_player.login
        sub_payload["subject_player"] = subject_player.login
        payload = dict()
        payload["promoted"] = sub_payload
        await manager.match_writer(
            group_identifier=group_identifier, dictionary=payload
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
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return

    location = request.location
    sub_dict = dict()
    sub_dict["location_information"] = location.dict()
    sub_dict["login"] = login
    location_dict = dict()
    location_dict["location"] = sub_dict

    await manager.match_writer(
        group_identifier=group_identifier, dictionary=location_dict
    )

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


async def inventory_update(
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    """update inventory every 5 seconds per player"""
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return

    inventory = request.inventory
    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return
    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].inventory = inventory
    await redis_client.set(name=key, value=str(m.dict()))

    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def prayer_update(
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    """update prayer player"""
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return

    prayer = request.prayer
    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return
    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].prayer = prayer
    await redis_client.set(name=key, value=str(m.dict()))

    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)

async def stats_update(
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return

    stats = request.stats
    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return
    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].stats = stats
    await redis_client.set(name=key, value=str(m.dict()))
    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def equipment_update(
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    """update equipment every 5 seconds per player"""
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return

    equipment = request.equipment
    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return
    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].equipment = equipment
    await redis_client.set(name=key, value=str(m.dict()))

    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def ping_update(group_identifier, request: models.request, manager, login):
    if group_identifier == "0":
        return
    ping = request.ping_payload.dict()
    payload = {"detail": "incoming ping", "ping_data": ping}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def chat(
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return
    chat = request.chat_message
    precensored, chat.message = await clean_text(chat.message)
    chat.username = login
    chat.timestamp = int(time.time())
    chat_payload = {"detail": "incoming chat", "chat_data": chat.dict()}

    sub_payload = dict()
    sub_payload["login"] = login
    sub_payload["message"] = precensored
    payload = dict()
    payload["chat"] = sub_payload
    await manager.match_writer(group_identifier=group_identifier, dictionary=payload)

    await manager.broadcast(group_identifier=group_identifier, payload=chat_payload)


async def search_request(request: models.request, websocket, login, manager):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    await manager.match_writer(
        group_identifier="0", key="search_request", value=f"{login}"
    )
    data = await search_match(search=request.search)
    if data is None:
        await websocket.send_json(
            {
                "detail": "search match data",
                "search_match_data": dict(),
            }
        )
        await manager.disconnect(websocket=websocket, group_identifier="0")
        return
    await manager.match_writer(
        group_identifier="0", key="search_send", value=f"{login}"
    )
    await websocket.send_json(
        {
            "detail": "search match data",
            "search_match_data": data.dict(),
        }
    )
    await manager.disconnect(websocket=websocket, group_identifier="0")


async def quick_match(request: models.request, websocket, login, manager):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return

    await manager.match_writer(
        group_identifier="0", key="quick_match", value=f"{login}"
    )
    match_list = request.match_list
    if not match_list:
        return

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


async def create_match_request(
    request: models.request, websocket, user_data, login, manager
):
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    await manager.match_writer(
        group_identifier="0", key="create_match", value=f"{login}"
    )
    initial_match = await create_match(request, user_data)

    history_initial_match = dict()
    history_initial_match["match_id"] = initial_match.ID
    history_initial_match["activity"] = initial_match.activity
    history_initial_match["max_players"] = initial_match.party_members
    history_initial_match["is_private"] = initial_match.isPrivate
    history_initial_match["notes"] = initial_match.notes
    history_initial_match["RuneGuard"] = initial_match.RuneGuard
    history_initial_match["match_version"] = initial_match.match_version
    history_initial_match["experience"] = initial_match.requirement.experience
    history_initial_match["split_type"] = initial_match.requirement.split_type
    history_initial_match["account_types"] = initial_match.requirement.accounts
    history_initial_match["regions"] = initial_match.requirement.regions

    match_creation_dict = dict()
    match_creation_dict["match_settings"] = history_initial_match
    match_creation_dict["login"] = login

    await manager.match_writer(
        group_identifier=initial_match.ID, dictionary=match_creation_dict
    )

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


async def gamestate_update(
    group_identifier, request: models.request, user_id, manager, websocket, login
):
    """update gamestate per player"""
    if not await ratelimit(connecting_IP=websocket.client.host):
        return
    if group_identifier == "0":
        return

    gamestate = int(request.gamestate)
    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return
    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].gamestate = gamestate

    await redis_client.set(name=key, value=str(m.dict()))
    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def update_status(
    group_identifier, request: models.request, websocket, user_id, login, manager
):
    if group_identifier == "0":
        return
    if not await ratelimit(connecting_IP=websocket.client.host):
        return

    key, m = await get_match_from_ID(group_identifier=group_identifier)
    if not m:
        return

    i = 0
    players = m.players
    for idx, player in enumerate(players):
        if player.user_id == user_id:
            i = idx
    m.players[i].status = request.status
    await redis_client.set(name=key, value=str(m.dict()))

    payload = {"detail": "match update", "match_data": m.dict()}
    await manager.broadcast(group_identifier=group_identifier, payload=payload)


async def check_connection_request(
    group_identifier, websocket, user_data, user_id, manager
):
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

    login = user_data["login"]

    await manager.match_writer(
        group_identifier=group_identifier,
        key="check_connection_request",
        value=f"successful connection from {login}",
    )
    await websocket.send_json(
        {"detail": "successful connection", "match_data": m.dict()}
    )


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


async def search_match(search: str):
    search = search.strip()
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
    ID = matchID()
    match_version = configVars.MATCH_VERSION

    discord = user_data["discord"]
    user_id = user_data["user_id"]
    verified = user_data["verified"]
    runewatch = user_data["runewatch"]
    wdr = user_data["wdr"]
    login = user_data["login"]

    activity = request.create_match.activity
    party_members = request.create_match.party_members
    experience = request.create_match.experience
    split_type = request.create_match.split_type
    accounts = request.create_match.accounts
    regions = request.create_match.regions
    RuneGuard = request.create_match.RuneGuard
    precensored, notes = await clean_text(request.create_match.notes)
    group_passcode = request.create_match.group_passcode
    private = bool(group_passcode)

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


async def post_match_to_discord(match: models.match):

    match_privacy = "Private" if match.isPrivate else "Public"
    activity = match.activity.replace("_", " ").title()
    precensored, notes = await clean_text(match.notes)

    webhook_payload = {
        "content": f"<@&{activityReference.pi_dict[match.activity]}> <t:{int(time.time())}:R>",
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
