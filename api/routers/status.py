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
    is_valid_rsn,
    verify_user_agent,
    verify_token_construction,
    verify_token,
)
from fastapi import APIRouter, HTTPException, Query, status, Request, Header

from pydantic import BaseModel
from pydantic.fields import Field
import re

router = APIRouter()

ONLINE = "alive"
MAINTENANCE = "maintenance"


@router.get("/V1/server-status/", tags=["status"])
async def get_server_health(
    login: str, token: str, user_agent: str | None = Header(default=None)
) -> json:

    if not await verify_user_agent(user_agent=user_agent):
        return

    user_id = await verify_token(login=login, token=token, access_level=0)

    return {"detail": ONLINE}
