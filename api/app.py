import logging

from fastapi_utils.tasks import repeat_every

import api.middleware
from api.config import app, redis_client
from api.routers import discord, lobby, status
from api.routers.lobby import manager
from api.utilities.utils import (
    load_redis_from_sql,
    automatic_match_cleanup,
    get_runewatch_bans,
    get_wdr_bans,
)

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
    await automatic_match_cleanup(manager=manager)


@app.on_event("startup")
@repeat_every(seconds=3600, wait_first=True, raise_exceptions=True)
async def ban_collection():
    try:
        await get_wdr_bans()
        await get_runewatch_bans()
        logger.info(f"Ban collection finished.")
    except Exception as e:
        logger.warning(f"Ban collection has failed. {e}")
        pass


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NeverScapeAlone api! If you're interested in becoming a developer, please contact ferrariictweet@gmail.com!"
    }
