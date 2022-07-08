from cgitb import text
from datetime import datetime
import json
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional
from h11 import InformationalResponse
import os

from pyparsing import Opt
from requests import request

from api.database.functions import (
    verify_user_agent,
    verify_token,
)
from fastapi import APIRouter, Header, Request

from pydantic import BaseModel
from pydantic.fields import Field
from api.config import redis_client

router = APIRouter()

ONLINE = "alive"
MAINTENANCE = "maintenance"


@router.get("/V1/server-status/", tags=["status"])
async def get_server_health(
    login: str,
    discord: str,
    token: str,
    user_agent: str | None = Header(default=None),
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return

    await verify_token(login=login, discord=discord, token=token, access_level=0)

    return {"detail": ONLINE}


@router.get("/V1/server-status/connections", tags=["status"])
async def get_server_health() -> json:
    minute_connections = await redis_client.keys("minute:*")
    hour_connections = await redis_client.keys("hour:*")
    minute_connections_count, hour_connections_count = len(minute_connections), len(
        hour_connections
    )
    return {
        "minute_connections": minute_connections_count,
        "hour_connections": hour_connections_count,
    }
