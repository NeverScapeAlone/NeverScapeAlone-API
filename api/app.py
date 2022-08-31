import logging

from fastapi_utils.tasks import repeat_every

import api.middleware
from api.config import app, redis_client
from api.routers import discord, lobby, status
from api.routers.lobby import manager
from api.utilities.utils import load_redis_from_sql, automatic_match_cleanup

app.include_router(discord.router)
app.include_router(status.router)
app.include_router(lobby.router)

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def redis_health_check():
    if await redis_client.ping():
        logging.info("REDIS SERVER CONNECTED!")
    else:
        logging.critical("REDIS SERVER IS NOT ACCESSIBLE!")


@app.on_event("startup")
@repeat_every(seconds=5, wait_first=True, raise_exceptions=True)
async def load_tables_into_redis():
    await load_redis_from_sql()
    await manager.cleanup_connections()


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NeverScapeAlone api! If you're interested in becoming a developer, please contact ferrariictweet@gmail.com!"
    }
