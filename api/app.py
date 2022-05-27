import api.middleware
from api.config import app
from api.routers import (
    request_history,
    user_rating_history,
    user_token,
    users,
)

app.include_router(request_history.router)
app.include_router(user_rating_history.router)
app.include_router(user_token.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NeverScapeAlone api! If you're interested in becoming a developer, please contact ferrariictweet@gmail.com!"
    }
