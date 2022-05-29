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
    verify_token,
)
from fastapi import APIRouter, HTTPException, Query, status, Request
from pydantic import BaseModel
from pydantic.fields import Field

router = APIRouter()


@router.get("/V1/server-status/", tags=["status"])
async def get_server_health(login: str, token: str, request: Request) -> json:

    if not await verify_token(login=login, token=token, access_level=0):
        return

    return {"status": "alive"}
