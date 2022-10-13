import logging

from api.config import redis_client
from api.database.database import USERDATA_ENGINE
from api.database.models import Users
from api.utilities.mysql.utils import sqlalchemy_result
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

logger = logging.getLogger(__name__)


async def load_redis_from_sql():

    table = Users
    sql = select(table)
    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            data = await session.execute(sql)
    data = sqlalchemy_result(data).rows2dict()

    mapping = dict()
    for value in data:
        user_id = value["user_id"]
        login = value["login"]
        key = f"user:{login}:{user_id}"
        del value["timestamp"]
        mapping[key] = str(value)
    if not mapping:
        return
    await redis_client.mset(mapping=mapping)
