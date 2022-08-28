import json
import logging
import time
from tokenize import group
from typing import List

from api.config import configVars, redis_client
from api.utilities.utils import get_match_from_ID, ratelimit, sha256, socket_userID
from fastapi import APIRouter, WebSocket, status

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections = dict()
        self.afk_sockets = dict()

    async def connect(self, websocket: WebSocket, group_identifier: str, passcode: str):
        """connect user to group"""
        await websocket.accept()

        if not await ratelimit(connecting_IP=websocket.client.host):
            return

        # catch statement for if the group already exists, and a connection has already been made, should prevent connection stacking.
        if group_identifier in list(self.active_connections.keys()):
            if websocket in self.active_connections[group_identifier]:
                logger.info(f"{login} >>< {group_identifier}")
                return

        login = websocket.headers["Login"]

        if group_identifier != "0":
            key, m = await get_match_from_ID(group_identifier=group_identifier)
            if not m:
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": "No Data"},
                    }
                )
                sub_payload = dict()
                sub_payload["login"] = login
                sub_payload["error"] = "No Match Data"
                payload = dict()
                payload["join_error"] = sub_payload
                await self.match_writer(
                    group_identifier=group_identifier, dictionary=payload
                )
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return
            if m.ban_list:
                user_id = await socket_userID(websocket=websocket)
                if user_id in m.ban_list:
                    await websocket.send_json(
                        {
                            "detail": "global message",
                            "server_message": {"message": "Banned from Group"},
                        }
                    )
                    sub_payload = dict()
                    sub_payload["login"] = login
                    sub_payload["error"] = "Banned from Group"
                    payload = dict()
                    payload["join_error"] = sub_payload
                    await self.match_writer(
                        group_identifier=group_identifier, dictionary=payload
                    )
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return
            if (m.isPrivate) & (m.group_passcode != passcode):
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": "Incorrect Passcode"},
                    }
                )
                sub_payload = dict()
                sub_payload["login"] = login
                sub_payload["error"] = "Incorrect Passcode"
                payload = dict()
                payload["join_error"] = sub_payload
                await self.match_writer(
                    group_identifier=group_identifier, dictionary=payload
                )
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return
            if len(m.players) >= int(m.party_members):
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": "Group Full"},
                    }
                )
                sub_payload = dict()
                sub_payload["login"] = login
                sub_payload["error"] = "Group Full"
                payload = dict()
                payload["join_error"] = sub_payload
                await self.match_writer(
                    group_identifier=group_identifier, dictionary=payload
                )
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return

        try:
            self.active_connections[group_identifier].append(websocket)
            await self.match_writer(
                group_identifier=group_identifier,
                key="successful_join",
                value=f"{login}",
            )
        except KeyError:
            self.active_connections[group_identifier] = [websocket]
            await self.match_writer(
                group_identifier=group_identifier,
                key="successful_join",
                value=f"{login}",
            )

    async def disconnect(self, websocket: WebSocket, group_identifier: str):
        """disconnect current socket"""
        login = websocket.headers["Login"]
        user_id = await socket_userID(websocket=websocket)

        if group_identifier not in list(self.active_connections.keys()):
            return

        if websocket in self.active_connections[group_identifier]:
            self.active_connections[group_identifier].remove(websocket)

        if group_identifier != "0":
            d = dict()
            d["disconnect"] = login
            await self.match_writer(group_identifier=group_identifier, dictionary=d)

            key, m = await get_match_from_ID(group_identifier=group_identifier)
            if not m:
                return
            for idx, player in enumerate(m.players):
                if player.user_id == user_id:
                    m.players.remove(player)
                    # check if player is party lead, if so assign to next
            if not self.active_connections[group_identifier]:
                del self.active_connections[group_identifier]
            if not m.players:
                await redis_client.delete(key)
                return
            await redis_client.set(name=key, value=str(m.dict()))

        try:
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception as e:
            pass

    async def disconnect_other_user(
        self, group_identifier: str, user_to_disconnect: str
    ):
        """disconnect another socket and remove player from group"""

        if group_identifier == "0":
            return

        subject_socket = None
        for socket in self.active_connections[group_identifier]:
            if socket.headers["Login"] == user_to_disconnect.login:
                subject_socket = socket

        if not subject_socket:
            return

        key, m = await get_match_from_ID(group_identifier=group_identifier)

        if not m:
            return

        for idx, player in enumerate(m.players):
            if player.user_id == user_to_disconnect.user_id:
                m.players.remove(player)

        if not m.ban_list:
            m.ban_list = [player.user_id]
        else:
            m.ban_list.append(player.user_id)
        await redis_client.set(name=key, value=str(m.dict()))

        subject_login = subject_socket.headers["Login"]
        sub_payload = dict()
        sub_payload["login"] = subject_login
        payload = dict()
        payload["forceful_socket_disconnect"] = sub_payload
        await self.match_writer(group_identifier=group_identifier, dictionary=payload)

        await subject_socket.send_json(
            {
                "detail": "global message",
                "server_message": {"message": "You have been kicked"},
            }
        )

        await subject_socket.close(code=status.WS_1000_NORMAL_CLOSURE)

    async def get_all_matches(self):
        return [key for key in self.active_connections.keys()]

    async def dissolve_match(self, group_identifier: str, disconnect_message: str):
        """disconnect all sockets and delete match"""

        key, m = await get_match_from_ID(group_identifier=group_identifier)
        if not key:
            return (
                f"{group_identifier} does not exist, and therefore cannot be deleted."
            )

        # if the group identifier doesn't exist in manager, forcefully delete match
        if group_identifier not in list(self.active_connections.keys()):
            if await redis_client.delete(key):
                return f"{group_identifier} was unmanaged and forcefully deleted."

        # remove all socket connections and delete users in those sockets
        for websocket in self.active_connections[group_identifier]:
            try:
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": f"{disconnect_message}"},
                    }
                )
                await self.disconnect(
                    websocket=websocket,
                    group_identifier=group_identifier,
                    disconnect_message=disconnect_message,
                )
            except:
                pass
        if await redis_client.delete(key):
            return f"{group_identifier} was managed and forcefully deleted."
        return f"{group_identifier} was managed and cleanly deleted."

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

    async def afk_update(self, websocket: WebSocket, group_identifier: str):
        """updates the afk timer in self.afk_sockets, if this value gets too high the socket is disconnected."""
        user_agent = websocket.headers["User-Agent"]
        plugin_version = websocket.headers["Version"]
        token = websocket.headers["Token"]
        key = sha256(string=f"{user_agent}{plugin_version}{token}{group_identifier}")
        self.afk_sockets[key] = (time.time(), websocket, group_identifier)

    async def cleanup_connections(self):
        key_list = list(self.afk_sockets.keys())  # prevents RunTime error from occuring
        for key in key_list:
            try:
                (old_time, websocket, group_identifier) = self.afk_sockets[key]
                if time.time() > old_time + configVars.TIMEOUT:
                    del self.afk_sockets[key]
                    login = websocket.headers["Login"]
                    await self.match_writer(
                        group_identifier=group_identifier,
                        key="afk_cleanup",
                        value=f"{login}",
                    )
                    if group_identifier != "0":
                        await websocket.send_json(
                            {
                                "detail": "global message",
                                "server_message": {"message": "AFK Disconnect"},
                            }
                        )
                    await self.disconnect(
                        websocket=websocket, group_identifier=group_identifier
                    )
            except Exception as e:
                logger.info(e)
                pass

    async def check_connection(
        self, websocket: WebSocket, group_identifier: str
    ) -> bool:
        """connection sanity check"""
        if group_identifier not in list(self.active_connections.keys()):
            logger.info(f"{group_identifier} is not being managed")
            return False
        if websocket not in self.active_connections[group_identifier]:
            logger.info(f"websocket in {group_identifier} does not exist")
            return False
        return True

    async def match_writer(
        self, group_identifier: str, key=None, value=None, dictionary=None
    ):
        path = "./histories/"
        filename = f"{group_identifier}.json"
        file = path + filename
        with open(file=file, mode="a+") as match_history:
            if key is not None and value is not None:
                d = dict()
                d[key] = value
                d["time"] = time.time()
                json_object = json.dumps(d, indent=4)
            if dictionary:
                dictionary["time"] = time.time()
                json_object = json.dumps(dictionary, indent=4)
            match_history.write(json_object)
            match_history.write(",")
