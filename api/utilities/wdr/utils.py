import json
import logging
import requests

from api.database.database import USERDATA_ENGINE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


async def get_wdr_bans():
    data = requests.get("https://wdrdev.github.io/banlist.json")
    json_array = json.loads(data.content)

    payload_list = []
    for json_data in json_array:
        login = "'" + json_data["CURRENT RSN"] + "'"
        wdr = "'" + json_data["Category"].replace("'", "") + "'"
        s = "(" + login + "," + wdr + ")"
        payload_list.append(s)

    null_query = text(f"""UPDATE users SET runewatch = null WHERE 1=1""")
    insert_query = text(
        f"""INSERT INTO users (login, wdr) VALUES {", ".join(payload_list)} ON DUPLICATE KEY UPDATE wdr = VALUES(wdr);"""
    )

    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(null_query)
            await session.execute(insert_query)
