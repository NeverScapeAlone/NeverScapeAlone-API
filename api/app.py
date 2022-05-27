import api.middleware
from api.config import app
from api.routers import (
    request_history,
    user_rating_history,
    user_token,
    user_points,
    options_boss,
    options_minigame,
    options_misc,
    options_skill,
    users,
)

app.include_router(request_history.router)
app.include_router(user_rating_history.router)
app.include_router(user_token.router)
app.include_router(user_points.router)
app.include_router(users.router)
app.include_router(options_boss.router)
app.include_router(options_minigame.router)
app.include_router(options_misc.router)
app.include_router(options_skill.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NeverScapeAlone api! If you're interested in becoming a developer, please contact ferrariictweet@gmail.com!"
    }
