import json
import logging
import os
import sys
import warnings

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from logging.handlers import RotatingFileHandler
from fastapi.middleware.cors import CORSMiddleware
import aioredis

# load environment variables
load_dotenv(find_dotenv(), verbose=True)


class Configuration:
    def __init__(self):
        self.sql_uri = os.environ.get("sql_uri")
        self.GLOBAL_BROADCAST_TOKEN = os.environ.get("global_broadcast_token")
        self.DISCORD_TOKEN = os.environ.get("discord_route_token")
        self.DISCORD_WEBHOOK = os.environ.get("discord_webhook")
        self.REDIS_PASSWORD = os.environ.get("redis_password")
        self.REDIS_DATABASE = os.environ.get("redis_database")
        self.RATE_LIMIT_MINUTE = 120
        self.RATE_LIMIT_HOUR = 7200
        self.MATCH_VERSION = "v3.0.0-alpha"
        self.TIMEOUT = 30 * 60  # 30 min afk timer

    def setMATCH_VERSION(self, match_version):
        self.MATCH_VERSION = match_version


configVars = Configuration()


redis_client = aioredis.from_url(
    url="redis://touchgrass.online",
    port=6379,
    db=configVars.REDIS_DATABASE,
    password=configVars.REDIS_PASSWORD,
)

# create application
app = FastAPI(
    title="NeverScapeAlone",
    version=f"{configVars.MATCH_VERSION}",
    contact={
        "name": "NeverScapeAlone",
        "url": "https://twitter.com/NeverScapeAlone",
        "email": "ferrariictweet@gmail.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

file_handler = logging.FileHandler(filename="logs/error.log", mode="a")
stream_handler = logging.StreamHandler(sys.stdout)

# log formatting
formatter = logging.Formatter(
    json.dumps(
        {
            "ts": "%(asctime)s",
            "name": "%(name)s",
            "function": "%(funcName)s",
            "level": "%(levelname)s",
            "msg": json.dumps("%(message)s"),
        }
    )
)


file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

handlers = [file_handler, stream_handler]

logging.basicConfig(level=logging.DEBUG, handlers=handlers)

# set imported loggers to warning
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.DEBUG)

logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("aiomysql").setLevel(logging.ERROR)

logging.getLogger("uvicorn.error").propagate = False


# https://github.com/aio-libs/aiomysql/issues/103
# https://github.com/coleifer/peewee/issues/2229
warnings.filterwarnings("ignore", ".*Duplicate entry.*")
