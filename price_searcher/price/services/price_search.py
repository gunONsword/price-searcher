import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests


def _sanitize_keyword(keyword: str) -> str:
    """Fix keywords that trigger Rakuten API 'wrong_parameter' error.

    Known bad patterns:
    - Trailing single letter:  'RTX 4090 D'       -> 'RTX 4090D'
    - Middle single digit:     'Ryzen 9 9900X'    -> 'Ryzen 9900X'
                               'Core Ultra 5 225F'-> 'Core Ultra 225F'
      The 2022 API rejects keywords that contain a standalone single-character
      token (one character surrounded by spaces). This affects all AMD Ryzen
      (Ryzen 5/7/9 ...) and Intel Core Ultra (Ultra 5/7/9 ...) keywords.
    """
    k = keyword.strip()
    # "RTX 4090 D" -> "RTX 4090D"  (merge trailing single letter)
    k = re.sub(r"\s+([A-Za-z])$", r"\1", k)
    # "Ryzen 9 9900X" -> "Ryzen 9900X"  (remove middle standalone single digit)
    k = re.sub(r"\s+\d\s+", " ", k)
    return k


def _get_rakuten_app_id():
    """Read after Django settings (and .env) are loaded."""
    return (os.getenv("RAKUTEN_APP_ID") or "").strip()


def _get_rakuten_access_key():
    """Access key (pk_...) for 2022 API. Optional if using legacy app-id only."""
    return (os.getenv("RAKUTEN_ACCESS_KEY") or "").strip()


def _is_valid_app_id(app_id):
    """Check if app_id is a valid numeric format (legacy API needs this)."""
    # Legacy API needs numeric app_id, not UUID
    return app_id.isdigit() and len(app_id) >= 10


# Rakuten genre: 100081 = グラフィックボード (Graphics board). Web mall search uses no genre = whole mall.
RAKUTEN_GENRE_ID = "100081"


def _search_rakuten_legacy(keyword: str, application_id: str, genre_id: str | None = RAKUTEN_GENRE_ID, min_price: int | None = None):
    """Legacy Ichiba API (20170706). genre_id=None = search whole mall (like search.rakuten.co.jp/search/mall/)."""
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    params = {
        "applicationId": application_id,
        "keyword": keyword,
        "hits": 30,
    }
    if genre_id:
        params["genreId"] = genre_id
    if min_price and min_price > 0:
        params["minPrice"] = min_price
    for attempt in range(3):
        try:
            res = requests.get(url, params=params, timeout=30)
            break
        except (requests.Timeout, requests.ConnectionError):
            if attempt < 2:
                time.sleep(3)
                continue
            raise
    data = res.json()
    if "Items" not in data:
        err = data.get("error") or data.get("error_description") or data.get("Error") or str(data)[:200]
        if "wrong_parameter" in str(err):
            return []  # Keyword rejected by API, return empty
        raise ValueError(f"Rakuten legacy API: {err}")
    results = []
    for item in data.get("Items", []):
        item = item["Item"]
        results.append({
            "site": "Rakuten",
            "name": item["itemName"],
            "price": item["itemPrice"],
            "url": item["itemUrl"],
            "currency": "JPY",
        })
    return results


def _search_rakuten_2022_impl(app_id: str, access_key: str, keyword: str, genre_id: str | None = RAKUTEN_GENRE_ID, min_price: int | None = None):
    """2022 API implementation. genre_id=None = search whole mall (like search.rakuten.co.jp/search/mall/).
    Note: Some keywords (e.g. 'RTX 4090 D' with space) can trigger HTTP 400 wrong_parameter.
    """
    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": keyword,
        "sort": "+itemPrice",
        "formatVersion": "2",
        "hits": 30,
    }
    if genre_id:
        params["genreId"] = genre_id
    if min_price and min_price > 0:
        params["minPrice"] = min_price
    # 2022 API: Origin + Referer must match the app's "Allowed websites" (e.g. https://price-searcher.com)
    app_url = (os.getenv("RAKUTEN_APP_URL") or "http://localhost").strip().rstrip("/")
    headers = {
        "Origin": app_url,
        "Referer": app_url + "/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        last_err = None
        for attempt in range(3):
            try:
                res = requests.get(url, params=params, headers=headers, timeout=30)
            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_err = str(net_err)
                if attempt < 2:
                    time.sleep(3)
                    continue
                raise RuntimeError(f"Rakuten API network error after 3 retries: {last_err}") from net_err
            data = res.json() if res.content else {}
            if res.status_code == 200:
                break
            last_err = data.get("errors", {}).get("errorMessage") or data.get("error") or res.text[:150]
            # 400 wrong_parameter: try sanitized keyword once
            if res.status_code == 400 and "wrong_parameter" in str(last_err):
                sanitized = _sanitize_keyword(keyword)
                if sanitized != keyword:
                    print(f"[Rakuten] 400 wrong_parameter for '{keyword}', retrying as '{sanitized}'")
                    params["keyword"] = sanitized
                    keyword = sanitized
                    continue
                # Cannot fix, return empty results instead of raising
                print(f"[Rakuten] 400 wrong_parameter for '{keyword}', skipping")
                return []
            if res.status_code == 429 and attempt < 2:
                time.sleep(3)
                continue
            if res.status_code in (502, 503, 504) and attempt < 2:
                time.sleep(3)
                continue
            # On persistent 503, try legacy API as fallback
            if res.status_code == 503:
                try:
                    return _search_rakuten_legacy(keyword, access_key)
                except Exception:
                    pass
            # Return proper error for 403
            if res.status_code == 403:
                raise RuntimeError(f"Rakuten API HTTP 403: {data}")
            raise ValueError(f"Rakuten API HTTP {res.status_code}: {last_err}")
        if res.status_code != 200:
            raise ValueError(f"Rakuten API HTTP {res.status_code}: {last_err}")

        # formatVersion=2: response key is "Items" (capital I)
        items = data.get("Items") or data.get("items") or data.get("Products") or []
        if not isinstance(items, list):
            items = []
        results = []
        for item in items:
            # Handle wrapped format: [{"Item": {...}}, ...] (legacy-style in 2022 API)
            if "Item" in item and isinstance(item["Item"], dict):
                item = item["Item"]
            name = item.get("itemName") or item.get("productName") or item.get("title") or "—"
            price_raw = item.get("itemPrice") or item.get("price")
            if price_raw is None:
                continue
            try:
                price = int(price_raw)
            except (TypeError, ValueError):
                continue
            link = item.get("itemUrl") or item.get("productUrl") or item.get("url") or ""
            if not link:
                continue
            results.append({
                "site": "Rakuten",
                "name": name,
                "price": price,
                "url": link,
                "currency": "JPY",
            })
        return results
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Rakuten 2022 API search '{keyword}': {e}") from e


def _normalize_for_match(text: str) -> str:
    """Normalize for loose keyword match: upper case, collapse spaces, remove common separators."""
    if not text:
        return ""
    t = (text or "").upper().replace("\u3000", " ").replace("　", " ")
    return " ".join(t.split())


def _filter_results_by_keyword(results: list, keyword: str):
    """Keep only results whose name contains the keyword (case-insensitive, normalized)."""
    if not keyword or not keyword.strip():
        return results
    k = _normalize_for_match(keyword)
    out = []
    for r in results:
        name = _normalize_for_match(r.get("name") or "")
        # Require key tokens: e.g. "Ryzen 7 9800X3D" -> at least "9800" or "9800X3D" in name
        if k in name:
            out.append(r)
            continue
        # Loose: if keyword has digits, require the digit part to appear (e.g. 9800X3D)
        digit_part = re.search(r"\d+[A-Za-z0-9]*", k)
        if digit_part and digit_part.group() in name:
            out.append(r)
    return out if out else results  # If filter would remove all, return original


def search_rakuten(keyword, min_price: int | None = None):
    """
    Rakuten Ichiba Item Search API.
    First tries whole-mall search (like https://search.rakuten.co.jp/search/mall/...).
    Uses minPrice API parameter to filter out cheap accessories at the API level.

    Credentials needed in .env:
    - Legacy API: RAKUTEN_APP_ID = numeric ID (e.g., "1234567890123456")
    - 2022 API: RAKUTEN_APP_ID = UUID + RAKUTEN_ACCESS_KEY = pk_xxx

    IMPORTANT: If using 2022 API and get 403 (HTTP_REFERRER_NOT_ALLOWED),
    you need to whitelist your domain in Rakuten app settings.
    """
    app_id = _get_rakuten_app_id()
    access_key = _get_rakuten_access_key()

    if not app_id and not access_key:
        return []

    # Determine which API to use:
    # - 2022 API: has accessKey AND app_id is UUID format (not numeric)
    # - Legacy API: has numeric app_id OR no access_key
    use_2022 = bool(access_key and app_id and not _is_valid_app_id(app_id))

    def do_search(genre_id=None, use_min_price_in_api: bool = True):
        """use_min_price_in_api=False: do not send minPrice to API (get more hits), filter in Python instead."""
        api_min = min_price if (use_min_price_in_api and min_price and min_price > 0) else None
        if use_2022:
            return _search_rakuten_2022_impl(app_id, access_key, keyword, genre_id=genre_id, min_price=api_min)
        return _search_rakuten_legacy(keyword, app_id, genre_id=genre_id, min_price=api_min)

    def apply_min_price_filter(results: list) -> list:
        if not min_price or min_price <= 0:
            return results
        return [r for r in results if (r.get("price") or 0) >= min_price]

    if use_2022:
        print(f"[Rakuten] Using 2022 API (keyword={keyword}, minPrice={min_price})")
        try:
            # Whole mall with minPrice so cheap accessories don't fill the 30-item slot quota.
            # Without minPrice + sort=+itemPrice, cheap accessories mentioning the CPU name take all 30 slots.
            results = do_search(genre_id=None, use_min_price_in_api=True)
            results = _filter_results_by_keyword(results, keyword)
            results = apply_min_price_filter(results)
            if not results:
                # Fallback: try genre 100081 (graphics board) with minPrice in API
                print("[Rakuten] 0 results in whole-mall, trying genre 100081...")
                results = do_search(genre_id=RAKUTEN_GENRE_ID, use_min_price_in_api=True)
            return results
        except RuntimeError as e:
            # If 403 (Referer not allowed), try legacy API as fallback
            if "403" in str(e) and "HTTP_REFERRER_NOT_ALLOWED" in str(e):
                print("[Rakuten] 2022 API failed (Referer not allowed)")
                # Check if we have numeric app_id for legacy
                if _is_valid_app_id(app_id):
                    print("[Rakuten] Trying legacy API instead...")
                    try:
                        results = _search_rakuten_legacy(keyword, app_id, None, min_price=None)
                        results = _filter_results_by_keyword(results, keyword)
                        results = apply_min_price_filter(results)
                        if not results:
                            results = _search_rakuten_legacy(keyword, app_id, RAKUTEN_GENRE_ID, min_price=min_price)
                        return results
                    except Exception as legacy_err:
                        raise RuntimeError(f"Both 2022 and legacy API failed: {legacy_err}") from legacy_err
                else:
                    raise RuntimeError(
                        f"[Rakuten] 2022 API failed (403): Referer not allowed.\n"
                        f"   Solution options:\n"
                        f"   1. Go to https://webservice.rakuten.co.jp/app/list/ and add your domain to whitelist\n"
                        f"   2. OR use legacy API: set RAKUTEN_APP_ID to numeric ID (not UUID), remove RAKUTEN_ACCESS_KEY"
                    ) from e
            else:
                raise

    # Legacy API (numeric app_id or no access_key)
    if _is_valid_app_id(app_id):
        print(f"[Rakuten] Using legacy API (app_id={app_id})")
        results = do_search(genre_id=None, use_min_price_in_api=True)
        results = _filter_results_by_keyword(results, keyword)
        results = apply_min_price_filter(results)
        if not results:
            print("[Rakuten] 0 results in whole-mall, trying genre 100081...")
            results = do_search(genre_id=RAKUTEN_GENRE_ID, use_min_price_in_api=True)
        return results
    else:
        raise RuntimeError(
            f"No valid Rakuten credentials.\n"
            f"   Current app_id: '{app_id}' (not numeric)\n"
            f"   Current access_key: {'set' if access_key else 'not set'}\n"
            f"   Please check your .env file."
        )


def search_products(keyword, min_price: int | None = None):
    keyword = (keyword or "").strip()
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(search_rakuten, keyword, min_price),
        ]

        results = []
        for f in futures:
            results.extend(f.result())

    return {
        "keyword": keyword,
        "results": sorted(results, key=lambda x: x["price"]),
    }
