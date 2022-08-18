import json
import logging

from api.config import (
    redis_client,
)
from api.utilities.utils import (
    get_match_from_ID,
    ratelimit,
    socket_userID,
)
from fastapi import APIRouter, WebSocket

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
                await websocket.close(code=1000)
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
                    await websocket.close(code=1000)
                    return
            if (m.isPrivate) & (m.group_passcode != passcode):
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": "Incorrect Passcode"},
                    }
                )
                await websocket.close(code=1000)
                return
            if len(m.players) >= int(m.party_members):
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": "Group Full"},
                    }
                )
                await websocket.close(code=1000)
                return

        try:
            self.active_connections[group_identifier].append(websocket)
            logger.info(f"{login} >> {group_identifier}")
        except KeyError:
            self.active_connections[group_identifier] = [websocket]
            logger.info(f"{login} > {group_identifier}")

    async def disconnect(self, websocket: WebSocket, group_identifier: str):
        """disconnect current socket"""
        login = websocket.headers["Login"]
        user_id = await socket_userID(websocket=websocket)

        if group_identifier not in list(self.active_connections.keys()):
            return

        self.active_connections[group_identifier].remove(websocket)

        if group_identifier != "0":
            key, m = await get_match_from_ID(group_identifier=group_identifier)
            if not m:
                return
            for idx, player in enumerate(m.players):
                if player.user_id == user_id:
                    m.players.remove(player)
            if not self.active_connections[group_identifier]:
                del self.active_connections[group_identifier]
            if not m.players:
                await redis_client.delete(key)
                logger.info(f"{login} < {group_identifier}")
                return
            await redis_client.set(name=key, value=str(m.dict()))

        logger.info(f"{login} << {group_identifier}")
        try:
            # Try to disconnect socket, if it's already been disconnected then ignore and eat exception.
            await websocket.close(1000)
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

        logger.info(f"{user_to_disconnect.login} <<K {group_identifier}")
        await subject_socket.send_json(
            {
                "detail": "global message",
                "server_message": {"message": "You have been kicked"},
            }
        )

        await subject_socket.close(1000)

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
