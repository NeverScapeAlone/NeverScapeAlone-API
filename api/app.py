from sqlalchemy import true
import api.middleware
import api.database.functions as functions
from api.config import app
from api.routers import (
    request_history,
    matchmaking,
    user_queue,
    user_rating_history,
    user_token,
    user_points,
    users,
    status,
)
from fastapi_utils.tasks import repeat_every

app.include_router(request_history.router)
app.include_router(user_rating_history.router)
app.include_router(matchmaking.router)
app.include_router(user_token.router)
app.include_router(user_points.router)
app.include_router(user_queue.router)
app.include_router(users.router)
app.include_router(status.router)


@app.on_event("startup")
@repeat_every(seconds=5, raise_exceptions=True)
async def automated_tasks():
    """Every 5 seconds:
    1. Dump Queue for bad inputs
    2. Retrieve positive queues
    """
    await functions.automatic_user_queue_cleanup()
    await matchmaking.build_matchmaking_parties()


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NeverScapeAlone api! If you're interested in becoming a developer, please contact ferrariictweet@gmail.com!"
    }
