import time
from . import config


def has_active_subscription(username: str, cost: float = 0.0) -> bool:
    if not username:
        return False
    if username in config.ACCESS_USERS:
        return True
    return config.user_balances.get(username, 0.0) >= cost


def time_until_next_search(username: str) -> float:
    last_time = config.search_cooldowns.get(username, 0)
    return max(0, config.COOLDOWN_HOURS * 3600 - (time.time() - last_time))
