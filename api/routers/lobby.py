import logging
import re
import traceback

import websockets
from api.config import configVars
from api.routers.interactions.handler import handle_request
from api.utilities.manager import ConnectionManager
from api.utilities.utils import socket_userID, user
from fastapi import APIRouter, HTTPException, WebSocket, status
import time

logger = logging.getLogger(__name__)

router = APIRouter()

manager = ConnectionManager()


@router.get("/V2/global_broadcast")
async def global_broadcast(message: str, authorization_token: str):
    if authorization_token[:2] != "-:":
        return HTTPException(
            status_code=400,
            detail="Incorrect append, authorization must contain '-:' starter.",
        )
    authorization_token = authorization_token[2:]
    if authorization_token != configVars.GLOBAL_BROADCAST_TOKEN:
        return HTTPException(
            status_code=401, detail="Your authorization token is incorrect."
        )
    if message == configVars.GLOBAL_BROADCAST_TOKEN:
        return HTTPException(status_code=400, detail="You didn't mean to send that...")
    manager.global_broadcast(message=message)


@router.websocket("/V2/lobby/{group_identifier}/{passcode}")
async def websocket_endpoint(
    websocket: WebSocket, group_identifier: str, passcode: str
):
    await manager.connect(
        websocket=websocket, group_identifier=group_identifier, passcode=passcode
    )
    try:
        user_id = await socket_userID(websocket=websocket)
        if re.match("^(E:)", str(user_id)):
            error_message = user_id[2:]
            await websocket.send_json(
                {
                    "detail": "global message",
                    "server_message": {"message": error_message},
                }
            )
            await manager.disconnect(
                websocket=websocket, group_identifier=group_identifier
            )
            return

        user_data = await user(user_id)
        login = user_data["login"]

        while True:
            try:
                request = await websocket.receive_json()
            except Exception as e:
                logger.debug(f"{login} => {e}")
                await manager.disconnect(
                    websocket=websocket, group_identifier=group_identifier
                )
                return

            await handle_request(
                request=request,
                user_data=user_data,
                group_identifier=group_identifier,
                websocket=websocket,
                manager=manager,
            )

    except websockets.exceptions.ConnectionClosedOK:
        logger.debug(f"{websocket.client.host} => Normal Socket Closure")
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)
    except websockets.exceptions.ConnectionClosedError:
        logger.debug(f"{websocket.client.host} => Odd closure, not a concern.")
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)
    except Exception as e:
        logger.debug(f"{websocket.client.host} => {e}")
        print(traceback.format_exc())
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)
