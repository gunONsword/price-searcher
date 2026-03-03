"""
Japanese e-commerce price comparison module for computer parts.

Supports: Amazon Japan (PA-API 5.0), Rakuten Ichiba, Yahoo Shopping.
All API keys are read from environment variables.
Uses concurrent.futures.ThreadPoolExecutor for parallel requests.
"""

import hashlib
import hmac
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Result type and constants
# ---------------------------------------------------------------------------

@dataclass
class ProductItem:
    """Single product result from any platform."""
    site: str
    name: str
    price: int
    url: str
    currency: str = "JPY"


# Amazon Japan PA-API 5.0
# Docs: https://webservices.amazon.com/paapi5/documentation/
# Host for Japan: webservices.amazon.co.jp, Region: ap-northeast-1
# Requires: AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG (env)
AMAZON_HOST = "webservices.amazon.co.jp"
AMAZON_REGION = "ap-northeast-1"
AMAZON_MARKETPLACE = "www.amazon.co.jp"


def _aws_sigv4_sign(
    key: str,
    date_stamp: str,
    region_name: str,
    service_name: str,
) -> bytes:
    """Derive signing key for AWS Signature Version 4."""
    k_date = hmac.new(
        ("AWS4" + key).encode("utf-8"),
        date_stamp.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    k_region = hmac.new(k_date, region_name.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service_name.encode("utf-8"), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
    return k_signing


def _sign_amazon_request(
    method: str,
    host: str,
    path: str,
    payload: str,
    access_key: str,
    secret_key: str,
    region: str,
    service: str = "ProductAdvertisingAPI",
) -> tuple[str, str]:
    """
    Create x-amz-date and Authorization header for Amazon PA-API (AWS Sig V4).
    """
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    canonical_uri = path or "/"
    canonical_querystring = ""
    canonical_headers = (
        f"content-encoding:amz-1.0\n"
        f"content-type:application/json; charset=utf-8\n"
        f"host:{host}\n"
        f"x-amz-date:{amz_date}\n"
        f"x-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems\n"
    )
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
    canonical_request = (
        f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _aws_sigv4_sign(secret_key, date_stamp, region, service)
    signature = hmac.new(
        signing_key,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return amz_date, authorization


def search_amazon(keyword: str) -> list[dict[str, Any]]:
    """
    Search Amazon Japan via Product Advertising API 5.0 (SearchItems).

    API: POST https://webservices.amazon.co.jp/ with JSON body.
    Auth: AWS Signature Version 4 (Access Key + Secret Key).
    Env: AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG.
    On failure returns empty list (no exception).
    """
    access_key = os.environ.get("AMAZON_ACCESS_KEY") or os.environ.get("AMAZON_API_KEY")
    secret_key = os.environ.get("AMAZON_SECRET_KEY")
    partner_tag = os.environ.get("AMAZON_PARTNER_TAG")
    if not all((access_key, secret_key, partner_tag)):
        return []

    # PA-API 5.0: POST to root path, operation in x-amz-target header
    url = f"https://{AMAZON_HOST}/"
    payload = {
        "Keywords": keyword,
        "Marketplace": AMAZON_MARKETPLACE,
        "PartnerTag": partner_tag,
        "PartnerType": "Associates",
        "Resources": [
            "Images.Primary.Small",
            "ItemInfo.Title",
            "Offers.Listings.Price",
            "DetailPageURL",
        ],
        "SearchIndex": "Computers",
    }
    payload_str = json.dumps(payload)

    try:
        amz_date, authorization = _sign_amazon_request(
            "POST",
            AMAZON_HOST,
            "/",
            payload_str,
            access_key,
            secret_key,
            AMAZON_REGION,
        )
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "amz-1.0",
            "Host": AMAZON_HOST,
            "X-Amz-Date": amz_date,
            "X-Amz-Target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
            "Authorization": authorization,
        }
        resp = requests.post(
            url,
            data=payload_str.encode("utf-8"),
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Parse PA-API 5.0 SearchItems response
        results = []
        search_result = data.get("SearchResult", {})
        items = search_result.get("Items", [])
        for item in items:
            title = (item.get("ItemInfo", {}) or {}).get("Title", {})
            title_text = title.get("DisplayValue", "") if isinstance(title, dict) else str(title)
            offers = (item.get("Offers", {}) or {}).get("Listings", [])
            price_val = None
            if offers:
                listing = offers[0]
                price_info = (listing.get("Price", {}) or {}).get("DisplayAmount")
                if price_info:
                    # e.g. "¥59,800" -> 59800
                    nums = re.sub(r"[^\d]", "", str(price_info))
                    if nums:
                        price_val = int(nums)
            if price_val is None:
                continue
            detail_url = (item.get("DetailPageURL") or "").strip()
            if not detail_url:
                continue
            results.append({
                "site": "Amazon",
                "name": title_text or "—",
                "price": price_val,
                "url": detail_url,
                "currency": "JPY",
            })
        return results
    except Exception:
        return []


def search_rakuten(keyword: str) -> list[dict[str, Any]]:
    """
    Search Rakuten Ichiba (楽天市場) via Ichiba Item Search API.

    API: GET https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601
    Params: applicationId (required), keyword (required).
    Doc: https://webservice.rakuten.co.jp/documentation/ichiba-item-search
    Env: RAKUTEN_APP_ID (or applicationId).
    On failure returns empty list.
    """
    app_id = os.environ.get("RAKUTEN_APP_ID")
    if not app_id:
        return []

    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
    params = {
        "applicationId": app_id,
        "keyword": keyword,
        "sort": "+itemPrice",
        "formatVersion": "2",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # formatVersion=2: items in data.get("items") or root level
        items = data.get("items", data.get("Products", []))
        if not isinstance(items, list):
            items = []

        results = []
        for item in items:
            # Flattened structure may use itemName, itemPrice, itemUrl
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
    except Exception:
        return []


def search_yahoo(keyword: str) -> list[dict[str, Any]]:
    """
    Search Yahoo! Shopping (Yahooショッピング) via Shopping Web API v3.

    API: GET https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch
    Params: appid (required), query (keyword).
    Doc: https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html
    Env: YAHOO_APP_ID (appid).
    On failure returns empty list.
    """
    app_id = os.environ.get("YAHOO_APP_ID")
    if not app_id:
        return []

    url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    params = {
        "appid": app_id,
        "query": keyword,
        "results": 20,
        "sort": "+price",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # V3 response: hit (total), hits (list of items)
        hits = data.get("hits", [])
        if not isinstance(hits, list):
            hits = []

        results = []
        for hit in hits:
            name = hit.get("name") or hit.get("title") or "—"
            price_val = hit.get("price")
            if price_val is None:
                continue
            try:
                price = int(price_val)
            except (TypeError, ValueError):
                continue
            url_val = hit.get("url") or hit.get("link") or hit.get("itemUrl") or ""
            if not url_val:
                continue
            results.append({
                "site": "Yahoo",
                "name": name,
                "price": price,
                "url": url_val,
                "currency": "JPY",
            })
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Unified interface and concurrency
# ---------------------------------------------------------------------------

def search_products(keyword: str) -> dict[str, Any]:
    """
    Search multiple Japanese e-commerce platforms in parallel and return
    unified result sorted by price (low to high).

    Platforms: Amazon Japan, Rakuten Ichiba, Yahoo Shopping.
    Each platform runs in a thread; one failure does not affect others.
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return {"keyword": keyword, "results": []}

    all_results: list[dict[str, Any]] = []

    def run_amazon():
        return search_amazon(keyword)

    def run_rakuten():
        return search_rakuten(keyword)

    def run_yahoo():
        return search_yahoo(keyword)

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_platform = {
            executor.submit(run_amazon): "Amazon",
            executor.submit(run_rakuten): "Rakuten",
            executor.submit(run_yahoo): "Yahoo",
        }
        for future in as_completed(future_to_platform):
            try:
                items = future.result()
                if items:
                    all_results.extend(items)
            except Exception:
                pass

    # Sort by price ascending
    all_results.sort(key=lambda x: (x.get("price") or 0))

    return {
        "keyword": keyword,
        "results": all_results,
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(search_products("RTX 4070"))
