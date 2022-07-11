import json
import os
import time
from cgitb import text
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional

from api.config import redis_client
from api.database.functions import verify_token, verify_user_agent
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pyparsing import Opt
from requests import request

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
    """
    Check server status, chances are -- if you can ping this, you're alive.
    """

    if not await verify_user_agent(user_agent=user_agent):
        return

    await verify_token(login=login, discord=discord, token=token, access_level=0)

    return {"detail": ONLINE}


@router.get("/V1/server-status/connections", tags=["status"])
async def get_server_health() -> json:
    """
    Get active server connections
    """
    minute_connections = await redis_client.keys("minute:*")
    hour_connections = await redis_client.keys("hour:*")
    minute_connections_count, hour_connections_count = len(minute_connections), len(
        hour_connections
    )
    return {
        "minute_connections": minute_connections_count,
        "hour_connections": hour_connections_count,
        "time": time.time(),
    }


@router.get("/V1/server-status/echo", tags=["status"])
async def echo(
    echo_string: Optional[str] = Query(..., min_length=0, max_length=100),
) -> json:
    """
    Echo a string from the server
    """
    return {"echo": echo_string, "time": time.time()}
