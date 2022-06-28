import json
import os
from cgitb import text
from datetime import datetime
from optparse import Option
from pickletools import optimize
from pstats import Stats
from typing import Optional

from api.database.functions import verify_token, verify_user_agent
from fastapi import APIRouter, FastAPI, Header, WebSocket
from fastapi.responses import HTMLResponse
from h11 import InformationalResponse
from pydantic import BaseModel
from pydantic.fields import Field
from pyparsing import Opt
from requests import request

router = APIRouter()


@router.websocket("/party")
async def party_websocket(
    websocket: WebSocket,
    login: str,
    discord: str,
    token: str,
    party_identifier: str,
    user_agent: str | None = Header(default=None),
):
    await websocket.accept()

    if not await verify_user_agent(user_agent=user_agent):
        return
    await verify_token(login=login, discord=discord, token=token, access_level=0)

    while True:
        json_text = await websocket.receive_json()
        json = json.loads(json_text)
        print(json)
