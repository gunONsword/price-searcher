"""Live JPY <-> CNY exchange rate, cached to avoid hammering the upstream API.

JD.com prices are entered manually in CNY (see Keyword.jd_price_cny); this service
supplies the rate used to convert them to JPY for comparison with Rakuten prices.
"""
import datetime

import requests
from django.core.cache import cache

FRESH_CACHE_KEY = "exchange_rate_jpy_cny_fresh"
LAST_GOOD_CACHE_KEY = "exchange_rate_jpy_cny_last_good"
CACHE_TTL_SECONDS = 1800  # 30 minutes: how long a fetched rate is served without re-fetching
# Conservative fallback used only if we have never successfully fetched a rate
# and the upstream API is unreachable. Roughly the JPY->CNY rate as of early 2026.
FALLBACK_JPY_TO_CNY = 0.048

API_URL = "https://api.frankfurter.app/latest"


def _fetch_live_rate():
    """Return (jpy_to_cny, cny_to_jpy) from the upstream API, or None on failure."""
    try:
        res = requests.get(API_URL, params={"from": "JPY", "to": "CNY"}, timeout=8)
        res.raise_for_status()
        data = res.json()
        jpy_to_cny = float(data["rates"]["CNY"])
        if jpy_to_cny <= 0:
            return None
        return jpy_to_cny, 1.0 / jpy_to_cny
    except Exception as e:
        print(f"[ExchangeRate] fetch failed: {e}")
        return None


def get_exchange_rate():
    """
    Return {jpy_to_cny, cny_to_jpy, updated_at, source, stale}.
    - source="cache": served from the 30-minute fresh cache, no network call made.
    - source="live": fresh cache had expired, just fetched from the upstream API.
    - source="stale-cache": upstream fetch failed, served from the last known-good value.
    - source="fallback": upstream fetch failed and no rate has ever been fetched.
    """
    fresh = cache.get(FRESH_CACHE_KEY)
    if fresh:
        return {**fresh, "source": "cache", "stale": False}

    live = _fetch_live_rate()
    if live is not None:
        jpy_to_cny, cny_to_jpy = live
        payload = {
            "jpy_to_cny": round(jpy_to_cny, 6),
            "cny_to_jpy": round(cny_to_jpy, 4),
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        cache.set(FRESH_CACHE_KEY, payload, timeout=CACHE_TTL_SECONDS)
        cache.set(LAST_GOOD_CACHE_KEY, payload, timeout=None)
        return {**payload, "source": "live", "stale": False}

    last_good = cache.get(LAST_GOOD_CACHE_KEY)
    if last_good:
        return {**last_good, "source": "stale-cache", "stale": True}

    jpy_to_cny = FALLBACK_JPY_TO_CNY
    return {
        "jpy_to_cny": jpy_to_cny,
        "cny_to_jpy": round(1.0 / jpy_to_cny, 4),
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "source": "fallback",
        "stale": True,
    }
