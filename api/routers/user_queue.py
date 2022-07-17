# import json
# import queue
# import time
# from ast import Delete
# from cgitb import text
# from dataclasses import replace
# from datetime import datetime
# from optparse import Option
# from pickletools import optimize
# from pstats import Stats
# from typing import Optional
# from urllib.request import Request
# from xmlrpc.client import Boolean, boolean

# from api.config import redis_client
# from api.database.functions import (
#     USERDATA_ENGINE,
#     EngineType,
#     sqlalchemy_result,
#     verify_token,
#     verify_user_agent,
# )
# from api.database.models import ActiveMatches, UserQueue
# from certifi import where
# from fastapi import APIRouter, Header, HTTPException, Query, status
# from h11 import InformationalResponse
# from pydantic import BaseModel
# from pydantic.fields import Field
# from pymysql import Timestamp
# from pyparsing import Opt
# from requests import options, request
# from sqlalchemy import TEXT, TIMESTAMP, select, values
# from sqlalchemy.dialects.mysql import Insert
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import aliased
# from sqlalchemy.sql.expression import Select, delete, insert, select, update

# router = APIRouter()


# class sub_payload(BaseModel):
#     """inner layer for content"""

#     party_member_count: int
#     self_experience_level: int
#     partner_experience_level: int
#     us: bool
#     eu_central: bool
#     eu_west: bool
#     oceania: bool
#     f2p: bool
#     p2p: bool


# class content(BaseModel):
#     """Wrapper configuration for sub_payload"""

#     activity: str
#     configuration: sub_payload


# class queue_post(BaseModel):
#     """Wrapper for content"""

#     Payload: list[content]


# class input_values(BaseModel):
#     """flattened model for queue start"""

#     user_id: int
#     in_queue: bool
#     activity: str
#     party_member_count: int
#     self_experience_level: int
#     partner_experience_level: int
#     us: bool
#     eu_central: bool
#     eu_west: bool
#     oceania: bool
#     f2p: bool
#     p2p: bool


# @router.post("/V1/queue/start", tags=["matchmaking"])
# async def post_user_queue_start(
#     user_options: queue_post,
#     login: str = Query(..., min_length=1, max_length=12),
#     discord: str = Query(..., min_length=1, max_length=64),
#     token: str = Query(..., min_length=32, max_length=32),
#     user_agent: str | None = Header(default=None),
# ) -> json:

#     if not await verify_user_agent(user_agent=user_agent):
#         return
#     user_id = await verify_token(
#         login=login, discord=discord, token=token, access_level=0
#     )

#     incoming_content = user_options.Payload
#     for activities in incoming_content:
#         value = input_values(
#             user_id=user_id,
#             in_queue=True,
#             activity=activities.activity,
#             party_member_count=activities.configuration.party_member_count,
#             self_experience_level=activities.configuration.self_experience_level,
#             partner_experience_level=activities.configuration.partner_experience_level,
#             us=activities.configuration.us,
#             eu_central=activities.configuration.eu_central,
#             eu_west=activities.configuration.eu_west,
#             oceania=activities.configuration.oceania,
#             f2p=activities.configuration.f2p,
#             p2p=activities.configuration.p2p,
#         )

#         key = f"queue:{user_id}:{activities.activity}"
#         await redis_client.set(name=key, value=str(value.dict()), ex=21600)

#     return {"detail": "queue started"}


# @router.get("/V1/queue/cancel", tags=["matchmaking"])
# async def get_user_queue_cancel(
#     login: str = Query(..., min_length=1, max_length=12),
#     discord: str = Query(..., min_length=1, max_length=64),
#     token: str = Query(..., min_length=32, max_length=32),
#     route_type: Optional[str] = Query(None),
#     user_agent: str | None = Header(default=None),
# ) -> json:

#     if not await verify_user_agent(user_agent=user_agent):
#         return
#     user_id = await verify_token(
#         login=login, discord=discord, token=token, access_level=0
#     )

#     queue_keys = await redis_client.keys(f"queue:{user_id}:*")
#     active_matches_keys = await redis_client.keys(f"match:{user_id}:*")
#     keys = queue_keys + active_matches_keys
#     if keys:
#         await redis_client.delete(*keys)

#     if route_type == "end session":
#         return {"detail": "match ended"}
#     return {"detail": "queue canceled"}
