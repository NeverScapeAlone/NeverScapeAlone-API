import logging
import time

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.responses import Response
from urllib3 import HTTPResponse

from api.config import app, redis_client, RATE_LIMIT_MINUTE, RATE_LIMIT_HOUR
import json

logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_handler(request: Request, call_next):
    response = await redis_ratelimit(request=request)
    if response is not None:
        return response
    response = await process_request(request=request, call_next=call_next)
    return response


async def redis_ratelimit(request: Request):
    client_host = request.client.host

    minute = int(time.time() / 60)
    hour = int(time.time() / 3600)

    client_minute = f"minute:{client_host}:{minute}"
    client_hour = f"hour:{client_host}:{hour}"

    minute_hits, hour_hits = await redis_client.mget(keys=[client_minute, client_hour])

    if minute_hits is None:
        await redis_client.set(name=client_minute, value=0, ex=60)
    if hour_hits is None:
        await redis_client.set(name=client_hour, value=0, ex=3600)

    await redis_client.incr(name=client_minute, amount=1)
    await redis_client.incr(name=client_hour, amount=1)

    if (minute_hits is None) | (hour_hits is None):
        minute_hits, hour_hits = await redis_client.mget(
            keys=[client_minute, client_hour]
        )

    minute_hits = int(minute_hits)
    hour_hits = int(hour_hits)

    if (minute_hits > RATE_LIMIT_MINUTE) or (hour_hits > RATE_LIMIT_HOUR):
        logger.warning(
            {
                "client": client_host,
                "minute hits": minute_hits,
                "minute limit": RATE_LIMIT_MINUTE,
                "hour hits": hour_hits,
                "hour limit": RATE_LIMIT_HOUR,
            }
        )
        d = dict()
        d["detail"] = "rate limit"
        return JSONResponse(status_code=429, content=json.dumps(d))


async def process_request(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    url = request.url.remove_query_params("token")._url
    logger.debug({"url": url, "process_time": process_time})
    return response


async def redis_cache_response():
    return
