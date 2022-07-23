import json
import logging
from re import sub
from sys import int_info
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
from api.database.functions import redis_decode, verify_headers, sanitize
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
from h11 import ConnectionClosed, InformationalResponse
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
        self.active_connections = dict()

    async def connect(self, websocket: WebSocket, group_identifier: str, passcode: str):
        """connect user to group"""
        await websocket.accept()

        if group_identifier != "0":
            keys = await redis_client.keys(f"match:ID={group_identifier}*")
            values = await redis_client.mget(keys)
            match_data = await redis_decode(bytes_encoded=values)
            match_info = match_data[0]
            if match_info["isPrivate"]:
                if match_info["group_passcode"] != passcode:
                    await websocket.send_json({"detail": "bad passcode"})
                    await websocket.close(code=1000)

        login = websocket.headers["Login"]
        try:
            self.active_connections[group_identifier].append(websocket)
            logging.info(f"{login} > {group_identifier}")
        except KeyError:
            self.active_connections[group_identifier] = [websocket]
            logging.info(f"{login} >> {group_identifier}")

    def disconnect(self, websocket: WebSocket, group_identifier: str):
        """disconnect user from group"""
        login = websocket.headers["Login"]
        logging.info(f"{login} <| {group_identifier}")
        self.active_connections[group_identifier].remove(websocket)

    async def broadcast(self, group_identifier: id, payload: json):
        """broadcast info to group"""
        for connection in self.active_connections[group_identifier]:
            await connection.send_json(payload)


manager = ConnectionManager()


@router.get("/V2/active-groups")
async def active_groups():
    return str(manager.active_connections)


## TODO add manager and broadcast, cyclic data send.


@router.websocket("/V2/lobby/{group_identifier}/{passcode}")
async def websocket_endpoint(
    websocket: WebSocket, group_identifier: str, passcode: str
):
    await manager.connect(
        websocket=websocket, group_identifier=group_identifier, passcode=passcode
    )
    try:
        head = websocket.headers
        login = head["Login"]
        discord = head["Discord"]
        token = head["Token"]
        user_agent = head["user-agent"]

        user_id = await verify_headers(
            login=login,
            discord=discord,
            token=token,
            user_agent=user_agent,
        )

        if user_id is None:
            await websocket.send_json({"detail": "disconnected"})
            manager.disconnect(websocket=websocket, group_identifier=group_identifier)

        while True:
            request = await websocket.receive_json()
            match request["detail"]:
                case "search_match":
                    logging.info(f"{login} -> Search")
                    search = await sanitize(request["search"])
                    if not search:
                        continue
                    data = await search_match(search=search)
                    logging.info(f"{login} <- {data}")
                    await websocket.send_json(
                        {
                            "detail": "search match data",
                            "search_match_data": data.dict(),
                        }
                    )

                case "create_match":
                    logging.info(f"{login} -> Create Match")
                    initial_match = await create_match(request, user_id, login, discord)
                    key = f"match:ID={initial_match.ID}:ACTIVITY={initial_match.activity}:PRIVATE={initial_match.isPrivate}"
                    await redis_client.set(name=key, value=str(initial_match.dict()))
                    await websocket.send_json(
                        {
                            "detail": "request join new match",
                            "join": f"{initial_match.ID}",
                            "passcode": f"{initial_match.group_passcode}",
                        }
                    )

                case _:
                    await websocket.send_json({"detail": "successful connection"})
                    continue

    except WebSocketDisconnect or ConnectionResetError or ConnectionClosed:
        manager.disconnect(websocket=websocket, group_identifier=group_identifier)


class search_match_info(BaseModel):
    ID: str
    activity: str
    party_members: str
    isPrivate: bool
    experience: str
    split_type: str
    accounts: str
    regions: str
    player_count: str
    party_leader: str


class all_search_match_info(BaseModel):
    search_matches: List[search_match_info]


class stats(BaseModel):
    """player skills"""

    attack: int
    strength: int
    defense: int
    ranged: int
    prayer: int
    magic: int
    runecraft: int
    construction: int
    hp: int
    agility: int
    herblore: int
    thieving: int
    crafting: int
    fletching: int
    slayer: int
    hunter: int
    mining: int
    smithing: int
    fishing: int
    cooking: int
    firemaking: int
    woodcutting: int
    farming: int


class status(BaseModel):
    """player status"""

    hp: int
    prayer: int
    run_energy: int
    special_attack: int
    overhead_prayer: str


class player(BaseModel):
    """player model"""

    discord: Optional[str]
    stats: Optional[stats]
    status: Optional[status]
    runewatch: Optional[str]
    wdr: Optional[str]
    verified: Optional[bool]
    user_id: int
    login: str
    isPartyLeader: bool


class requirement(BaseModel):
    """match requirements"""

    experience: str
    split_type: str
    accounts: str
    regions: str


class match(BaseModel):
    """match model"""

    discord_invite: Optional[str]
    ID: str
    activity: str
    party_members: str
    group_passcode: str
    isPrivate: bool
    requirement: requirement
    players: list[player]


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

        val = search_match_info(
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

    data = all_search_match_info(search_matches=search_matches)
    return data


async def create_match(request, user_id, login, discord):
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

    initial_match = match(
        ID=ID,
        activity=activity,
        party_members=party_members,
        isPrivate=private,
        group_passcode=group_passcode,
        requirement=requirement(
            experience=experience,
            split_type=split_type,
            accounts=accounts,
            regions=regions,
        ),
        players=[
            player(
                discord="NONE" if discord is None else discord,
                isPartyLeader=True,
                user_id=user_id,
                login=login,
            )
        ],
    )
    return initial_match
