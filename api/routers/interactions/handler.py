import logging
import random

import api.database.models as models
from api.config import redis_client
from api.routers.interactions.functions import (
    like,
    dislike,
    kick,
    chat,
    promote,
    location_update,
    inventory_update,
    equipment_update,
    gamestate_update,
    ping_update,
    search_request,
    prayer_update,
    stats_update,
    quick_match,
    create_match_request,
    update_status,
    check_connection_request,
)
from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def handle_request(
    request: models.request,
    user_data: dict,
    group_identifier: str,
    websocket: WebSocket,
    manager,
):

    user_id = user_data["user_id"]
    login = user_data["login"]

    match request.detail:

        case "chat":
            await chat(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "like":
            await like(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
            )

        case "dislike":
            await dislike(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
            )

        case "kick":
            await kick(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
            )

        case "promote":
            await promote(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
            )

        case "player_location":
            await location_update(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "inventory_update":
            await inventory_update(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "prayer_update":
            await prayer_update(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "stats_update":
            await stats_update(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "gamestate_update":
            await gamestate_update(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "equipment_update":
            await equipment_update(
                group_identifier=group_identifier,
                request=request,
                user_id=user_id,
                manager=manager,
                websocket=websocket,
                login=login,
            )

        case "ping":
            await ping_update(
                group_identifier=group_identifier,
                request=request,
                manager=manager,
                login=login,
            )

        case "search_match":
            await search_request(
                request=request, websocket=websocket, login=login, manager=manager
            )

        case "quick_match":
            await quick_match(
                request=request, websocket=websocket, login=login, manager=manager
            )

        case "create_match":
            await create_match_request(
                request=request,
                websocket=websocket,
                user_data=user_data,
                login=login,
                manager=manager,
            )

        case "set_status":
            await update_status(
                group_identifier=group_identifier,
                request=request,
                websocket=websocket,
                user_id=user_id,
                login=login,
                manager=manager,
            )

        case "check_connection":
            await check_connection_request(
                group_identifier=group_identifier,
                websocket=websocket,
                user_data=user_data,
                user_id=user_id,
                manager=manager,
            )

        case _:
            return
