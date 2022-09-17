import ast
import hashlib
import logging
import re
import time
import string
from typing import Optional

import aiohttp
from api.config import configVars
from api.utilities.wordkey import WordKey
from better_profanity import profanity
from bs4 import BeautifulSoup
from pydantic import BaseModel

logger = logging.getLogger(__name__)
wordkey = WordKey()


class world_loader(BaseModel):
    world_number: int
    activity: str
    player_count: int
    p2p: int
    f2p: int
    us: int
    eu_central: int
    eu_west: int
    oceania: int


class userBanUpdate(BaseModel):
    login: str
    wdr: Optional[str]
    runewatch: Optional[str]


async def redis_decode(bytes_encoded) -> list:
    if type(bytes_encoded) == list:
        return [ast.literal_eval(element.decode("utf-8")) for element in bytes_encoded]
    return [ast.literal_eval(bytes_encoded.decode("utf-8"))]


async def verify_ID(user_id):
    user_id = str(user_id)
    if re.fullmatch("^[0-9]{0,64}", user_id):
        return True
    return False


async def post_url(route, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url=route, json=data) as resp:
            response = await resp.text()


async def clean_text(notes: str):
    if len(notes) > 200:
        notes = notes[:200]
        notes += "..."
    notes = profanity.censor(notes)
    notes = re.sub("<[^>]*>", "", notes)
    notes = notes.strip()
    return notes


def sha256(string: str) -> str:
    """sha256 encodes a string"""
    return hashlib.sha256(string.encode()).hexdigest()


async def get_plugin_version():
    """gets the most up-to-date NeverScapeAlone plugin version"""
    url = (
        "https://github.com/NeverScapeAlone/never-scape-alone/blob/master/build.gradle"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as resp:
            response = await resp.text()
    soup = BeautifulSoup(response, "html.parser")
    for s in soup.find_all(id=re.compile("^LC[0-9]")):
        if not s.find_all(string=re.compile("^version")):
            continue
        s = "".join(s.stripped_strings)
        match = re.match("^version[ ]{0,1}=[ ]{0,1}", s)
        if not match:
            continue
        version = s[match.span()[1] :].strip("'")
    return version


async def verify_user_agent(user_agent):
    if not re.fullmatch("^RuneLite", user_agent[:8]):
        return False
    return True


async def verify_plugin_version(plugin_version):
    if configVars.MATCH_VERSION[:2] == plugin_version[:2]:
        return True
    return False


async def is_valid_rsn(login: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{1,12}", login):
        return False
    return True


async def validate_discord(discord: str):
    if re.fullmatch(
        "^(?:[A-Za-z\d+/]{4})*(?:[A-Za-z\d+/]{3}=|[A-Za-z\d+/]{2}==)?$", discord
    ):
        return discord
    return False


async def verify_token_construction(token: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{32}", token):
        return False
    return True


async def verify_discord_id(discord_id: str) -> bool:
    if discord_id == "NULL":
        return True
    if not re.fullmatch("^[\d]*", discord_id):
        return False
    return True


async def sanitize(string: str) -> str:
    string = string.strip()
    if not string:
        return None
    string = string.upper()
    return string


def encode(num):
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    if num == 0:
        return alphabet[0]
    arr = []
    arr_append = arr.append
    _divmod = divmod
    base = len(alphabet)
    while num:
        num, rem = _divmod(num, base)
        arr_append(alphabet[rem])
    arr.reverse()
    return "".join(arr)


def matchID():
    ID = encode(time.time_ns())[5:][::-1]
    splits = [wordkey.key[ID[i : i + 2]] for i in range(0, len(ID), 2)]
    ID = "-".join(splits)
    return ID
