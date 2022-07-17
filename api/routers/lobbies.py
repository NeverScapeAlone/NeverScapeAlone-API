import json
import logging
import time
from ast import Delete
from dataclasses import replace
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional
from urllib.request import Request
from fastapi.responses import HTMLResponse
from typing import List
from xmlrpc.client import Boolean, boolean

import networkx as nx
import numpy as np
import pandas as pd
from api.config import VERSION, redis_client
from api.database.functions import verify_headers
from api.database.models import ActiveMatches, UserQueue, Users, WorldInformation
from api.routers import user_queue
from certifi import where
from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    status,
    WebSocketDisconnect,
)
from fastapi_utils.tasks import repeat_every
from h11 import InformationalResponse
from networkx.algorithms.community import greedy_modularity_communities
from pydantic import BaseModel
from pydantic.fields import Field
from pymysql import Timestamp
from pyparsing import Opt
from requests import delete, options, request, session
from sqlalchemy import TEXT, TIMESTAMP, select, table, tuple_, values
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case, text
from sqlalchemy.sql.expression import Select, insert, select, update

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/V2/lobby/{group_identifier}")
async def websocket_endpoint(websocket: WebSocket, group_identifier: str):
    await manager.connect(websocket)
    try:
        head = websocket.headers
        user_id = await verify_headers(
            login=head["Login"],
            discord=head["Discord"],
            token=head["Token"],
            user_agent=head["user-agent"],
        )

        if user_id is None:
            await manager.send_personal_message("invalid value", websocket=websocket)
            manager.disconnect(websocket=websocket)

        while True:
            request = await websocket.receive_json()
            print(request)
            match request["detail"]:
                # default
                case _:
                    continue

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client left the chat")
