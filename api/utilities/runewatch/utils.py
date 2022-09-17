import json
import logging
import requests

from api.database.database import USERDATA_ENGINE, Engine
from api.utilities.wordkey import WordKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


async def get_runewatch_bans():
    data = requests.get("https://runewatch.com/api/v2/rsn")
    json_nested = json.loads(data.content)

    payload_list = []
    for group in json_nested:
        array_payload = json_nested[group][0]
        login = "'" + array_payload["rsn"].replace("'", "") + "'"
        runewatch = "'" + array_payload["type"].replace("'", "") + "'"
        s = "(" + login + "," + runewatch + ")"
        payload_list.append(s)

    null_query = text(f"""UPDATE users SET runewatch = null WHERE 1=1""")
    insert_query = text(
        f"""INSERT INTO users (login, runewatch) VALUES {", ".join(payload_list)} ON DUPLICATE KEY UPDATE runewatch = VALUES(runewatch);"""
    )
    async with USERDATA_ENGINE.get_session() as session:
        session: AsyncSession = session
        async with session.begin():
            await session.execute(null_query)
            await session.execute(insert_query)
