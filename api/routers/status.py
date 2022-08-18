import json
import time
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()

ONLINE = "alive"
MAINTENANCE = "maintenance"


@router.get("/V1/server-status/echo", tags=["status"])
async def echo(
    echo_string: Optional[str] = Query(..., min_length=0, max_length=100),
) -> json:
    """
    Echo a string from the server
    """
    return {"echo": echo_string, "time": time.time()}
