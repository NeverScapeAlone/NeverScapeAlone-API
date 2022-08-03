import json
import logging
import random
import time
import traceback
import sys

from api.config import VERSION, redis_client
from api.database.functions import (
    redis_decode,
    sanitize,
    ratelimit,
    user,
    verify_ID,
    get_rating,
    websocket_to_user_id,
)
from fastapi import APIRouter, WebSocket
import api.database.models as models

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections = dict()

    async def connect(self, websocket: WebSocket, group_identifier: str, passcode: str):
        """connect user to group"""
        await websocket.accept()

        if not await ratelimit(connecting_IP=websocket.client.host):
            return

        login = websocket.headers["Login"]

        if group_identifier != "0":
            keys = await redis_client.keys(f"match:ID={group_identifier}*")
            values = await redis_client.mget(keys)
            match_data = await redis_decode(bytes_encoded=values)
            if not match_data:
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": "No Data"},
                    }
                )
                return
            match_info = match_data[0]
            if match_info["isPrivate"]:
                if match_info["group_passcode"] != passcode:
                    await websocket.send_json(
                        {
                            "detail": "global message",
                            "server_message": {"message": "Incorrect Passcode"},
                        }
                    )
                    await websocket.close(code=1001)
                    return

        try:
            self.active_connections[group_identifier].append(websocket)
            logging.info(f"{login} >> {group_identifier}")
        except KeyError:
            self.active_connections[group_identifier] = [websocket]
            logging.info(f"{login} > {group_identifier}")

    async def disconnect(self, websocket: WebSocket, group_identifier: str):
        """disconnect user"""
        login = websocket.headers["Login"]
        user_id = await websocket_to_user_id(websocket=websocket)

        self.active_connections[group_identifier].remove(websocket)

        if group_identifier != "0":
            key = f"match:ID={group_identifier}*"
            matches = await redis_client.keys(key)
            if not matches:
                return
            match_key = matches[0]
            raw_data = await redis_client.get(match_key)
            data = await redis_decode(bytes_encoded=raw_data)
            m = models.match.parse_obj(data[0])
            for idx, player in enumerate(m.players):
                if player.user_id == user_id:
                    m.players.remove(player)
            if not self.active_connections[group_identifier]:
                del self.active_connections[group_identifier]
            if not m.players:
                await redis_client.delete(match_key)
                logging.info(f"{login} < {group_identifier}")
                return
            await redis_client.set(name=match_key, value=str(m.dict()))

        logging.info(f"{login} << {group_identifier}")

    async def broadcast(self, group_identifier: id, payload: json):
        """send message to all clients in group"""
        if group_identifier in list(self.active_connections.keys()):
            for connection in self.active_connections[group_identifier]:
                await connection.send_json(payload)

    async def global_broadcast(self, message: str):
        """send message to all clients on list"""
        payload = {"detail": "global message", "server_message": {"message": message}}
        keys = list(self.active_connections.keys())
        for group_id in keys:
            if group_id != "0":
                for connection in self.active_connections[group_id]:
                    await connection.send_json(payload)
        return {"detail": "sent"}


manager = ConnectionManager()


@router.websocket("/V2/lobby/{group_identifier}/{passcode}")
async def websocket_endpoint(
    websocket: WebSocket, group_identifier: str, passcode: str
):
    await manager.connect(
        websocket=websocket, group_identifier=group_identifier, passcode=passcode
    )
    try:
        user_id = await websocket_to_user_id(websocket=websocket)
        user_data = await user(user_id)
        login = user_data["login"]

        if user_id is None:
            await websocket.send_json(
                {
                    "detail": "global message",
                    "server_message": {"message": "You have been disconnected"},
                }
            )
            await manager.disconnect(
                websocket=websocket, group_identifier=group_identifier
            )

        while True:
            try:
                request = await websocket.receive_json()
                print(request)
            except Exception as e:
                logging.debug(f"{login} => {e}")
                await manager.disconnect(
                    websocket=websocket, group_identifier=group_identifier
                )
                return

            match request["detail"]:

                case "like":
                    like_id = request["like"]
                    if not await verify_ID(user_id=like_id):
                        continue
                    if like_id == str(user_id):
                        continue
                    key = f"rating:{like_id}:{user_id}"
                    await redis_client.set(name=key, value=int(1))

                case "dislike":
                    dislike_id = request["dislike"]
                    if not await verify_ID(user_id=dislike_id):
                        continue
                    if dislike_id == str(user_id):
                        continue
                    key = f"rating:{dislike_id}:{user_id}"
                    await redis_client.set(name=key, value=int(0))

                case "kick":
                    kick_id = request["kick"]
                    if not await verify_ID(user_id=kick_id):
                        continue
                    if kick_id == str(user_id):
                        continue

                case "promote":
                    promote_id = request["promote"]
                    if not await verify_ID(user_id=promote_id):
                        continue
                    if promote_id == str(user_id):
                        continue

                case "player_location":
                    if not await ratelimit(connecting_IP=websocket.client.host):
                        continue
                    if group_identifier == 0:
                        continue
                    logging.info(f"{login} ->> Set Location")
                    location = request["location"]
                    location = models.location.parse_obj(location)

                    key = f"match:ID={group_identifier}*"
                    matches = await redis_client.keys(key)
                    if not matches:
                        break
                    match_key = matches[0]
                    raw_data = await redis_client.get(match_key)
                    data = await redis_decode(bytes_encoded=raw_data)
                    data = data[0]
                    m = models.match.parse_obj(data)
                    i = 0
                    players = m.players
                    for idx, player in enumerate(players):
                        if player.user_id == user_id:
                            i = idx
                    m.players[i].location = location

                    await redis_client.set(name=match_key, value=str(m.dict()))

                    payload = {"detail": "match update", "match_data": m.dict()}

                    await manager.broadcast(
                        group_identifier=group_identifier, payload=payload
                    )

                case "ping":
                    if group_identifier != 0:
                        ping_payload = request["ping_payload"]
                        ping = models.ping.parse_obj(ping_payload).dict()
                        payload = {"detail": "incoming ping", "ping_data": ping}
                        await manager.broadcast(
                            group_identifier=group_identifier, payload=payload
                        )

                case "search_match":
                    if not await ratelimit(connecting_IP=websocket.client.host):
                        continue
                    logging.info(f"{login} -> Search")
                    search = await sanitize(request["search"])
                    if not search:
                        continue
                    data = await search_match(search=search)
                    logging.info(f"{login} <- Search")
                    await websocket.send_json(
                        {
                            "detail": "search match data",
                            "search_match_data": data.dict(),
                        }
                    )

                case "quick_match":
                    if not await ratelimit(connecting_IP=websocket.client.host):
                        continue
                    logging.info(f"{login} -> Quick")
                    match_list = request["match_list"]

                    if "RANDOM" in match_list:
                        flat_keys = await redis_client.keys(
                            f"match:*ACTIVITY=*:PRIVATE=False"
                        )
                    else:
                        key_chain = []
                        for activity in match_list:
                            keys = await redis_client.keys(
                                f"match:*ACTIVITY={activity}:PRIVATE=False"
                            )
                            if keys:
                                key_chain.append(keys)
                        flat_keys = [key for keys in key_chain for key in keys]

                    if not flat_keys:
                        continue

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

                case "create_match":
                    if not await ratelimit(connecting_IP=websocket.client.host):
                        continue
                    logging.info(f"{login} -> Create Match")
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

                case "set_status":
                    if group_identifier == "0":
                        continue
                    if not await ratelimit(connecting_IP=websocket.client.host):
                        continue

                    logging.info(f"{login} ->> Set Status")
                    status_val = models.status.parse_obj(request["status"])

                    key = f"match:ID={group_identifier}*"
                    matches = await redis_client.keys(key)
                    if not matches:
                        break
                    match_key = matches[0]
                    raw_data = await redis_client.get(match_key)
                    data = await redis_decode(bytes_encoded=raw_data)
                    data = data[0]
                    m = models.match.parse_obj(data)
                    i = 0
                    players = m.players
                    for idx, player in enumerate(players):
                        if player.user_id == user_id:
                            i = idx
                    m.players[i].status = status_val

                    await redis_client.set(name=match_key, value=str(m.dict()))

                    payload = {"detail": "match update", "match_data": m.dict()}

                    await manager.broadcast(
                        group_identifier=group_identifier, payload=payload
                    )

                case "check_connection":
                    if group_identifier == "0":
                        continue

                    if not await ratelimit(connecting_IP=websocket.client.host):
                        continue

                    pattern = f"match:ID={group_identifier}*"
                    keys = await redis_client.keys(pattern=pattern)
                    if not keys:
                        continue
                    key = keys[0]
                    data = await redis_client.get(name=key)
                    data = await redis_decode(bytes_encoded=data)
                    data = data[0]

                    m = models.match.parse_obj(data)

                    i = 0
                    players = m.players
                    uids = [player.user_id for player in players]

                    rating = await get_rating(user_id=user_id)
                    if user_id not in uids:
                        p = models.player.parse_obj(user_data)
                        p.rating = rating
                        m.players.append(p)
                        data = m.dict()
                        await redis_client.set(name=key, value=str(data))

                    await websocket.send_json(
                        {"detail": "successful connection", "match_data": data}
                    )

                case _:
                    continue

    except Exception as e:
        logging.debug(f"{websocket.client.host} => {e}")
        print(traceback.format_exc())
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)


async def search_match(search: str):
    keys = await redis_client.keys(f"match:*ACTIVITY={search}*")
    keys = keys[:50]
    values = await redis_client.mget(keys)
    match_data = await redis_decode(values)

    search_matches = []
    for match in match_data:
        requirement = match["requirement"]

        for player in match["players"]:
            if player["isPartyLeader"] != True:
                continue
            party_leader = player["login"]

        val = models.search_match_info(
            ID=str(match["ID"]),
            activity=match["activity"],
            party_members=match["party_members"],
            isPrivate=match["isPrivate"],
            experience=requirement["experience"],
            split_type=requirement["split_type"],
            accounts=requirement["accounts"],
            regions=requirement["regions"],
            player_count=str(len(match["players"])),
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
    group_passcode = sub_payload["group_passcode"]
    private = False if (len(group_passcode) == 0) else True
    ID = int(time.time() ** 2)

    rating = await get_rating(user_id=user_id)

    initial_match = models.match(
        ID=ID,
        activity=activity,
        party_members=party_members,
        isPrivate=private,
        group_passcode=group_passcode,
        requirement=models.requirement(
            experience=experience,
            split_type=split_type,
            accounts=accounts,
            regions=regions,
        ),
        players=[
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
