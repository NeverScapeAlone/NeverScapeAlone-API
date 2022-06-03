import asyncio
import logging
import random
import re
import string
import sys
import traceback
from asyncio.tasks import create_task
from collections import namedtuple
from datetime import datetime, timedelta
from typing import List

from api.database.database import USERDATA_ENGINE, Engine, EngineType
from api.database.models import Users, UserToken
from fastapi import HTTPException
from sqlalchemy import Text, text
from sqlalchemy.exc import InternalError, OperationalError
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession
from sqlalchemy.sql.expression import insert, select

logger = logging.getLogger(__name__)


async def is_valid_rsn(login: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{1,12}", login):
        raise HTTPException(
            status_code=202,
            detail=f"bad rsn",
        )
    return True


async def verify_user_agent(user_agent):
    if not re.fullmatch("^RuneLite", user_agent[:8]):
        raise HTTPException(
            status_code=202,
            detail=f"bad header",
        )
    return True


async def verify_token_construction(token: str) -> bool:
    if not re.fullmatch("[\w\d\s_-]{32}", token):
        raise HTTPException(
            status_code=202,
            detail=f"bad token",
        )
    return True


async def verify_token(login: str, token: str, access_level=0) -> bool:
    """User verification request - this display's the user's access level and if they have permissions to access the content that they wish to view.

    Args:
        login (str): The username that is sending the auth request
        token (str): The auth token being sent by the user

    Returns:
        bool: True|False depending upon if the request was successful, or not.
    """

    sql = select(UserToken)
    sql = sql.where(UserToken.token == token)
    sql = sql.where(Users.login == login)
    sql = sql.join(Users, UserToken.user_id == Users.user_id)

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            request = await session.execute(sql)
            data = sqlalchemy_result(request)
            data = data.rows2dict()

    if len(data) == 0:
        raise HTTPException(status_code=202, detail="registering")

    auth_level = data[0]["auth_level"]
    if access_level > auth_level:
        raise HTTPException(
            status_code=401,
            detail=f"Insufficent permissions. You cannot access this content at your auth level.",
        )
    return True


async def parse_sql(
    sql, param: dict, has_return: bool, row_count: int, page: int
) -> tuple[Text, bool]:
    if isinstance(sql, Text):
        return sql
    elif isinstance(sql, str):
        has_return = True if sql.strip().lower().startswith("select") else False

        if has_return:
            # add pagination to every query
            # max number of rows = 100k
            row_count = row_count if row_count <= 100_000 else 100_000
            page = page if page >= 1 else 1
            offset = (page - 1) * row_count
            # add limit to sql
            sql = f"{sql} limit :offset, :row_count;"
            # add the param
            param["offset"] = offset
            param["row_count"] = row_count

        # parsing
        sql: Text = text(sql)
    return (sql,)


async def execute_sql(
    sql,
    param: dict = {},
    debug: bool = False,
    engine: Engine = USERDATA_ENGINE,
    row_count: int = 100_000,
    page: int = 1,
    has_return: bool = None,
    retry_attempt: int = 0,
):
    # retry breakout
    if retry_attempt >= 5:
        logger.debug({"message": "Too many retries"})
        return None

    sleep = retry_attempt * 5
    sql, has_return = await parse_sql(sql, param, has_return, row_count, page)

    try:
        async with engine.get_session() as session:
            session: AsyncSession = session
            async with session.begin():
                rows = await session.execute(sql, param)
                records = sql_cursor(rows) if has_return else None
    # OperationalError = Deadlock, InternalError = lock timeout
    except Exception as e:
        if isinstance(e, InternalError):
            e = e if debug else ""
            logger.debug(
                {"message": f"Lock, Retry Attempt: {retry_attempt}, retrying: {e}"}
            )
        elif isinstance(e, OperationalError):
            e = e if debug else ""
            logger.debug(
                {"message": f"Deadlock, Retry Attempt: {retry_attempt}, retrying {e}"}
            )
        else:
            logger.error({"message": "Unknown Error", "error": e})
            logger.error(traceback.print_exc())
            return None
        await asyncio.sleep(random.uniform(0.1, sleep))
        records = await execute_sql(
            sql,
            param,
            debug,
            engine,
            row_count,
            page,
            has_return=has_return,
            retry_attempt=retry_attempt + 1,
        )
    return records


class sql_cursor:
    def __init__(self, rows):
        self.rows: AsyncResult = rows

    def rows2dict(self):
        return self.rows.mappings().all()

    def rows2tuple(self):
        Record = namedtuple("Record", self.rows.keys())
        return [Record(*r) for r in self.rows.fetchall()]


class sqlalchemy_result:
    def __init__(self, rows):
        self.rows = [row[0] for row in rows]

    def rows2dict(self):
        return [
            {col.name: getattr(row, col.name) for col in row.__table__.columns}
            for row in self.rows
        ]

    def rows2tuple(self):
        columns = [col.name for col in self.rows[0].__table__.columns]
        Record = namedtuple("Record", columns)
        return [
            Record(*[getattr(row, col.name) for col in row.__table__.columns])
            for row in self.rows
        ]


async def batch_function(function, data, batch_size=100):
    """
    smaller transactions, can reduce locks, but individual transaction, can cause connection pool overflow
    """
    batches = []
    for i in range(0, len(data), batch_size):
        logger.debug({"batch": {f"{function.__name__}": f"{i}/{len(data)}"}})
        batch = data[i : i + batch_size]
        batches.append(batch)

    await asyncio.gather(*[create_task(function(batch)) for batch in batches])
    return


async def image_token_generator(length=10):
    return "".join(
        random.SystemRandom().choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits
        )
        for _ in range(length)
    )
