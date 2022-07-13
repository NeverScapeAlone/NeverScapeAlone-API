from urllib.request import Request
from sqlalchemy import true
import api.middleware
import api.database.functions as functions
from api.config import app, redis_client
from api.routers import (
    matchmaking,
    user_queue,
    user_token,
    status,
    discord,
)
import logging
from fastapi_utils.tasks import repeat_every

app.include_router(discord.router)
app.include_router(matchmaking.router)
app.include_router(user_token.router)
app.include_router(user_queue.router)
app.include_router(status.router)

logger = logging.getLogger(__name__)


@app.on_event("startup")
@repeat_every(seconds=5, wait_first=True, raise_exceptions=True)
async def automated_tasks():
    try:
        await functions.post_worlds()
        await functions.automatic_user_queue_cleanup()
        await matchmaking.build_matchmaking_parties()
        await functions.automatic_user_active_matches_cleanup()

        logger.info(f"Automated tasks finished.")

    except Exception as e:
        logger.warning(e)
        logger.info(f"Automated tasks have failed.")
        pass


@app.on_event("startup")
@repeat_every(seconds=3600, raise_exceptions=True)
async def ban_collection():
    try:
        await functions.get_wdr_bans()
        await functions.get_runewatch_bans()
        logger.info(f"Ban collection finished.")
    except Exception as e:
        logger.warning(e)
        logger.info(f"Ban collection has failed.")
        pass


@app.on_event("startup")
async def redis_health_check():
    if await redis_client.ping():
        logging.info("REDIS SERVER CONNECTED!")
    else:
        logging.critical("REDIS SERVER IS NOT ACCESSIBLE!")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NeverScapeAlone api! If you're interested in becoming a developer, please contact ferrariictweet@gmail.com!"
    }
