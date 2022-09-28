import json
import logging
import re
import traceback
from ast import MatchSingleton

import websockets
from api.config import configVars
from api.routers.interactions.handler import handle_request
from api.utilities.manager.manager import ConnectionManager
from api.utilities.manager.utils import socket_userID
from api.utilities.mysql.utils import user, validate_access_token
from api.utilities.utils import sha256
from api.database import models
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

router = APIRouter()

manager = ConnectionManager()


@router.get("/V2/match_history")
async def match_history(match_identifier: str, access_token: str):
    if not await validate_access_token(access_token=access_token):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Access.",
        )
    if not re.fullmatch("^[a-z]{2,7}-[a-z]{2,7}-[a-z]{2,7}", match_identifier):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect Match Identifier format. Expected: ^[a-z]{2,7}-[a-z]{2,7}-[a-z]{2,7}",
        )
    path = "./histories/"
    filename = f"{match_identifier}.json"
    file = path + filename
    try:
        with open(file=file, mode="r") as match_history:
            info = match_history.read()
            info = info.replace("\n", "")
            info = info.strip(",")
            contents = f"""{{"match_history":[{info}]}}"""
            data = json.loads(contents)
    except FileNotFoundError:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match history not found.",
        )
    return data


@router.get("/V2/update-version")
async def update_version(version: str, access_token: str):
    if not await validate_access_token(access_token=access_token):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Access.",
        )

    old_match_version = configVars.MATCH_VERSION
    configVars.MATCH_VERSION = version
    return {
        "old_match_version": old_match_version,
        "new_match_version": configVars.MATCH_VERSION,
    }


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
            try:
                await websocket.send_json(
                    {
                        "detail": "global message",
                        "server_message": {"message": error_message},
                    }
                )
            except Exception as e:
                logger.error(f"Unable to notify user on first-connection: {e}")
                pass

            await manager.disconnect(
                websocket=websocket, group_identifier=group_identifier
            )
            return

        user_data = await user(user_id)
        login = user_data["login"]
        await manager.afk_update(websocket=websocket, group_identifier=group_identifier)

        while True:
            try:
                request = await websocket.receive_json()
                request = models.request.parse_obj(request)

                if not await manager.check_connection(
                    websocket=websocket, group_identifier=group_identifier
                ):
                    return
                await manager.afk_update(
                    websocket=websocket, group_identifier=group_identifier
                )
            except WebSocketDisconnect:
                logger.info(f"Client has closed connection: {login}")
                await manager.disconnect(
                    websocket=websocket, group_identifier=group_identifier
                )
                return
            except Exception as e:
                logger.info(
                    f"There was an error parsing the incoming request: {login} | {e}"
                )
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
        logger.debug(f"{sha256(websocket.client.host)} => Normal Connection Closed")
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)
    except websockets.exceptions.ConnectionClosedError:
        logger.debug(f"{sha256(websocket.client.host)} => Odd Connection Closed")
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)
    except Exception as e:
        logger.error(f"{sha256(websocket.client.host)} => {e}")
        print(traceback.format_exc())
        await manager.disconnect(websocket=websocket, group_identifier=group_identifier)
