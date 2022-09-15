import json
import logging
import time
from tokenize import group
from typing import List

from api.config import configVars, redis_client
from api.utilities.utils import get_match_from_ID, ratelimit, sha256, socket_userID
from fastapi import APIRouter, WebSocket, status, websockets

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """This is the connection manager for the NeverScapeAlone-API

    This connection manager class has the purpose of managing individual and group socket connections for the underlying match data.
    Graphically, this can be represented by:

    --- users or user groups ---
    --- ^^^^^^^^^^^^^^^^^^^^ ---
    ---  connection manager* ---
    --- ^^^^^^^^^^^^^^^^^^^^ ---
    ---   match info REDIS   ---
    * You are here.

    The connection manager is initialized on API restart and start-up. Therefore, any matches in 'memory' or those that are managed, will be cleared.
    If a match is cleared from the managed pool, it is still possible that it can exist in the 'match info' bottom-most layer. The connection manager
    should be able to facilicate a reconnection request from the users in the first layer, to the underlying match info layer. Additionally,
    if all users of the match above leave, or request closure, or there is an external admin closure request, then the connection manager will appropriately
    close the underlying match information, and disconnect all relevant users to the group.
    """

    def __init__(self):
        """active connections handeled by the manager"""
        self.active_connections = dict()
        """ afk sockets handeled by the afk section of the manager """
        self.afk_sockets = dict()

    async def connect(self, websocket: WebSocket, group_identifier: str, passcode: str):
        """connect user to group"""
        await websocket.accept()

        # if the user has been rate-limited, then there will be a denied connection.
        if not await ratelimit(connecting_IP=websocket.client.host):
            return

        # catch statement for if the group already exists, and a connection has already been made, should prevent connection stacking.
        if group_identifier in list(self.active_connections.keys()):
            if websocket in self.active_connections[group_identifier]:
                return

        login = websocket.headers["Login"]

        # if the match is a valid match (with ID greater than default "0")
        if group_identifier != "0":

            # should there be no match data, as in the match was deleted - or no data could be retrieved,
            # the client should be notified and the connection should be disbanded.
            key, m = await get_match_from_ID(group_identifier=group_identifier)
            if not m:
                logger.info(f"{login} has no data on {group_identifier}")
                try:
                    await websocket.send_json(
                        {
                            "detail": "global message",
                            "server_message": {"message": "No Data"},
                        }
                    )
                except Exception as e:
                    logger.error(f"Unable to notify user of no data: {e}")
                    pass
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

            # if the client is on the ban list for this group, they will be denied a connection.
            if m.ban_list:
                user_id = await socket_userID(websocket=websocket)
                if user_id in m.ban_list:
                    logger.info(
                        f"Banned user {login} has attempted to join {group_identifier}"
                    )
                    try:
                        await websocket.send_json(
                            {
                                "detail": "global message",
                                "server_message": {"message": "Banned from Group"},
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Unable to notify user that they're banned from the group: {e}"
                        )
                        pass
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

            # if the match is private, and there is a passcode requirement, failure to indicate the correct password leads to disconnect.
            if (m.isPrivate) & (m.group_passcode != passcode):
                logger.info(
                    f"{login} has entered the wrong passcode on {group_identifier}"
                )
                try:
                    await websocket.send_json(
                        {
                            "detail": "global message",
                            "server_message": {"message": "Incorrect Passcode"},
                        }
                    )
                except Exception as e:
                    logger.error(f"Unable to notify user of bad passcode: {e}")
                    pass
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

            # if the number of players is at maximum or higher than maximum alloted, notify the client and disconnect socket.
            if len(m.players) >= int(m.party_members):
                logger.info(
                    f"{login} has attempted to join a full group: {group_identifier}"
                )
                try:
                    await websocket.send_json(
                        {
                            "detail": "global message",
                            "server_message": {"message": "Group Full"},
                        }
                    )
                except Exception as e:
                    logger.error(f"Unable to notify user that group is full: {e}")
                    pass

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

        # attempt to add the socket connection to the roster, if this fails in the case of a new match being created
        # then create the dictionary, in both cases respond to the client with a successful join.
        try:
            self.active_connections[group_identifier].append(websocket)
            await self.match_writer(
                group_identifier=group_identifier,
                key="successful_join",
                value=f"{login}",
            )
            logger.info(f"{login} has joined group: {group_identifier}")
        except KeyError:
            self.active_connections[group_identifier] = [websocket]
            await self.match_writer(
                group_identifier=group_identifier,
                key="successful_join",
                value=f"{login}",
            )
            logger.info(f"{login} has joined group: {group_identifier}")

    async def disconnect(self, websocket: WebSocket, group_identifier: str):
        """disconnect a socket from the connection pool"""
        login = websocket.headers["Login"]
        user_id = await socket_userID(websocket=websocket)

        # if the requested match does not exist, return nothing and ignore the request. Ex. disconnect user from an unmanaged match.
        # that does not exist in the connection manager's memory (Headless Match) The number of headless instantly following API restart
        # is precisely 100%, as the internal memory for the connection manager has been reset, though the match data may still exist in the
        # redis cache layer.

        if group_identifier not in list(self.active_connections.keys()):
            return

        # Attempt to close the socket connection, this may fail for a variety of reasons, and should be logged accordingly.
        try:
            logger.info(f"Disconnecting {login} from {group_identifier}")
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except RuntimeError as e:
            # No need to log anything, the connection has already been closed.
            pass
        except Exception as e:
            logger.error(
                f"Websocket Closure Error: {e}",
            )
            pass

        # remove the socket from the connection manager's roster. This is indicated for memory management
        # and so that broadcasting does not return a null error of a prior closed connection. Failure to resolve this case
        # can lead to a variety of connditions, namely exceptions which would lead to stacking disconnections.
        if websocket in self.active_connections[group_identifier]:
            self.active_connections[group_identifier].remove(websocket)

        # remove the corresponding websocket's player object from the relevant match data.
        # this prevents 'headless players' from being within the match, while their data may exist,
        # the player itself would be unmanaged, and therefore could not be interacted with.
        if group_identifier != "0":
            d = dict()
            d["disconnect"] = login
            await self.match_writer(group_identifier=group_identifier, dictionary=d)

            key, m = await get_match_from_ID(group_identifier=group_identifier)
            if not m:
                return
            for idx, player in enumerate(m.players):
                if player.user_id == user_id:
                    if (player.isPartyLeader) & (len(m.players) > 1):
                        m.players.remove(player)
                        m.players[0].isPartyLeader = True
                    else:
                        m.players.remove(player)

            # If the length of connection manager dictionary's list is 0, then remove this match from the connection manager.
            if group_identifier in list(self.active_connections.keys()):
                if not self.active_connections[group_identifier]:
                    del self.active_connections[group_identifier]

            # delete the match data from the database, when all players have left the group.
            if not m.players:
                await redis_client.delete(key)
                return
            await redis_client.set(name=key, value=str(m.dict()))

    async def disconnect_other_user(
        self, group_identifier: str, user_to_disconnect: str
    ):
        """disconnect another socket and remove player from group"""

        # don't disconnect other users from default...
        if group_identifier == "0":
            return

        # find the subject socket in the list of websockets from the active connections
        subject_socket = None
        for socket in self.active_connections[group_identifier]:
            if socket.headers["Login"] == user_to_disconnect.login:
                subject_socket = socket

        # if there is no relevant socket, return
        if not subject_socket:
            return

        # get the current match information from the ID
        key, m = await get_match_from_ID(group_identifier=group_identifier)

        # if it doesn't exist, ex. the match has been deleted, just return
        if not m:
            return

        # remove the player from the match data
        for idx, player in enumerate(m.players):
            if player.user_id == user_to_disconnect.user_id:
                m.players.remove(player)

        # add the player to the ban list
        if not m.ban_list:
            m.ban_list = [player.user_id]
        else:
            m.ban_list.append(player.user_id)

        # update the match data
        await redis_client.set(name=key, value=str(m.dict()))

        # log it
        subject_login = subject_socket.headers["Login"]
        sub_payload = dict()
        sub_payload["login"] = subject_login
        payload = dict()
        payload["forceful_socket_disconnect"] = sub_payload
        await self.match_writer(group_identifier=group_identifier, dictionary=payload)

        # try to send the kicked player some message that they've been removed
        try:
            logger.info(f"Kicking {user_to_disconnect} from {group_identifier}")
            await subject_socket.send_json(
                {
                    "detail": "global message",
                    "server_message": {"message": "You have been kicked"},
                }
            )
        except Exception as e:
            logger.error(f"Sending message to kicked player error: {e}")
            pass

        # close the subject's socket
        try:
            await subject_socket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception as e:
            logger.error(f"Removing kicked player's socket error: {e}")
            pass

    async def get_all_matches(self):
        return [key for key in self.active_connections.keys()]

    async def dissolve_match(self, group_identifier: str, disconnect_message: str):
        """disconnect all sockets and delete match"""

        logger.info(f"Attempting to dissolve group: {group_identifier}")

        key, m = await get_match_from_ID(group_identifier=group_identifier)
        if not key:
            logger.info(
                f"{group_identifier} does not exist, and therefore cannot be deleted."
            )
            return (
                f"{group_identifier} does not exist, and therefore cannot be deleted."
            )

        # if the group identifier doesn't exist in manager, forcefully delete match
        if group_identifier not in list(self.active_connections.keys()):
            if await redis_client.delete(key):
                logger.info(f"{group_identifier} was unmanaged and forcefully deleted.")
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
            except Exception as e:
                logging.error(f"Failed sending disconnect message to user: {e}")
                pass

        if await redis_client.delete(key):
            return f"{group_identifier} was managed and cleanly deleted."
        return f"{group_identifier} was managed and forcefully deleted."

    async def broadcast(self, group_identifier: id, payload: json):
        """send message to all clients in group"""
        if group_identifier in list(self.active_connections.keys()):
            for connection in self.active_connections[group_identifier]:
                try:
                    await connection.send_json(payload)
                except Exception as e:
                    logger.error(
                        f"Unable to broadcast information to a connection: {e}"
                    )
                    pass

    async def global_broadcast(self, message: str):
        """send message to all clients on list"""
        keys = list(self.active_connections.keys())
        for group_id in keys:
            if group_id != "0":
                for connection in self.active_connections[group_id]:
                    try:
                        await connection.send_json(
                            {
                                "detail": "global message",
                                "server_message": {"message": f"{message}"},
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Unable to broadcast information to a connection: {e}"
                        )
                        pass
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
                        try:
                            await websocket.send_json(
                                {
                                    "detail": "global message",
                                    "server_message": {"message": "AFK Disconnect"},
                                }
                            )
                        except Exception as e:
                            logger.error(
                                f"Unable to notify user of AFK disconnect: {e}"
                            )
                            pass
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
