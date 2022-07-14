from sqlalchemy import true
from api.config import app, redis_client
from api.routers import (
    matchmaking,
    user_queue,
    user_token,
    status,
    discord,
)
import logging

app.include_router(discord.router)
app.include_router(matchmaking.router)
app.include_router(user_token.router)
app.include_router(user_queue.router)
app.include_router(status.router)

logger = logging.getLogger(__name__)


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
