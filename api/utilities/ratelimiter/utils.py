import logging

from api.config import redis_client
from api.utilities.utils import sha256

logger = logging.getLogger(__name__)


async def ratelimit(connecting_IP):
    MAX_CALLS_SECOND = 10
    """load key formats"""
    key = sha256(string=f"ratelimit_call:{connecting_IP}")
    manager_key = sha256(string=f"ratelimit_manager:{connecting_IP}")
    tally_key = sha256(string=f"ratelimit_tally:{connecting_IP}")

    """ load stopgate for ratelimit tally """
    tally_data = await redis_client.get(tally_key)
    if tally_data is not None:
        return False

    """ check current rate """
    data = await redis_client.get(key)
    if data is None:
        """first time in call period, start new key"""
        await redis_client.set(name=key, value=int(1), ex=1)
        return True

    if int(data) > MAX_CALLS_SECOND:
        """exceeded per second call rate, elevate to rate manager"""
        manager_data = await redis_client.get(manager_key)
        if manager_data is None:
            """no previously set manager, due to expired watch"""
            await redis_client.set(name=manager_key, value=int(2), ex=2)
            await redis_client.set(name=tally_key, value=int(1), ex=1)
            return False

        """ previously known rate manager, advance manager """
        manager_amount = int(manager_data)
        manager_amount = manager_amount * 2  # Raise difficulty
        tally_amount = int(manager_amount / 2)  # Half difficulty for tally amount

        await redis_client.set(
            name=manager_key, value=manager_amount, ex=manager_amount
        )
        await redis_client.set(name=tally_key, value=tally_amount, ex=tally_amount)
        return False

    value = 1 + int(data)
    await redis_client.set(name=key, value=value, xx=True, keepttl=True)
    return True
