"""Aggregate daily low/avg/max price and min-price URL from DailyPriceSnapshot."""
from datetime import date as date_type

from django.db.models import Avg, Max, Min

from price.models import DailyPriceSnapshot, DailyPriceSummary, Keyword


def _upsert_summary_from_snapshots(qs):
    """
    For each (keyword, date, site) group in the given queryset, compute
    low/high/avg and upsert one DailyPriceSummary row.
    Returns the number of summary rows written.
    """
    groups = list(qs.values("keyword_id", "date", "site").distinct())
    written = 0
    for g in groups:
        rows = qs.filter(keyword_id=g["keyword_id"], date=g["date"], site=g["site"])
        agg = rows.aggregate(low=Min("price"), high=Max("price"), avg=Avg("price"))
        first = rows.order_by("price").first()
        if not first:
            continue
        DailyPriceSummary.objects.update_or_create(
            keyword_id=g["keyword_id"],
            date=g["date"],
            site=g["site"],
            defaults={
                "keyword_name": first.keyword_name or "",
                "category": first.category or Keyword.CATEGORY_GPU,
                "low_price": agg["low"] or 0,
                "high_price": agg["high"] or 0,
                "avg_price": round(agg["avg"] or 0),
                "min_price_url": first.url or "",
            },
        )
        written += 1
    return written


def archive_and_purge_old_snapshots():
    """
    Called at the start of every collection run.
    1. For each (keyword, date, site) in DailyPriceSnapshot where date < today,
       compute low/high/avg and upsert into DailyPriceSummary.
    2. Delete all DailyPriceSnapshot rows where date < today.
    Returns (archived_groups, deleted_rows).
    """
    today = date_type.today()
    old = DailyPriceSnapshot.objects.filter(date__lt=today)
    archived = _upsert_summary_from_snapshots(old)
    deleted_count, _ = old.delete()
    return archived, deleted_count


def get_daily_stats(keyword_name: str | None = None, keyword_id: int | None = None):
    """
    Return list of { date, low_price, high_price, avg_price, min_price_url, all_prices }
    for each day, combining DailyPriceSummary (history) + DailyPriceSnapshot (today).
    """
    if keyword_id:
        keyword = Keyword.objects.filter(pk=keyword_id).first()
    elif keyword_name:
        keyword = Keyword.objects.filter(name=keyword_name).first()
    else:
        return []
    if not keyword:
        return []

    out = {}

    # --- Historical rows from DailyPriceSummary (aggregate across all sites per day) ---
    for row in (
        DailyPriceSummary.objects.filter(keyword=keyword)
        .values("date")
        .annotate(low=Min("low_price"), high=Max("high_price"), avg=Avg("avg_price"))
        .order_by("date")
    ):
        d = row["date"].isoformat()
        out[d] = {
            "date": d,
            "low_price": row["low"],
            "high_price": row["high"],
            "avg_price": round(row["avg"] or 0),
            "min_price_url": (
                DailyPriceSummary.objects.filter(keyword=keyword, date=row["date"])
                .order_by("low_price").values_list("min_price_url", flat=True).first() or ""
            ),
            "all_prices": [],
        }

    # --- Rows from DailyPriceSnapshot (may include un-archived historical dates) ---
    today = date_type.today()
    for d in (
        DailyPriceSnapshot.objects.filter(keyword=keyword)
        .values_list("date", flat=True)
        .distinct()
        .order_by("date")
    ):
        snapshots = DailyPriceSnapshot.objects.filter(keyword=keyword, date=d).order_by("price")
        all_prices = list(snapshots.values_list("price", flat=True))
        low_snap = snapshots.first()
        d_iso = d.isoformat()
        # Derive low/high/avg from all_prices so trend chart lines never contradict grey dots
        if all_prices:
            low_val = min(all_prices)
            high_val = max(all_prices)
            avg_val = round(sum(all_prices) / len(all_prices))
        else:
            agg = snapshots.aggregate(avg=Avg("price"), low=Min("price"), high=Max("price"))
            low_val = agg["low"] or (low_snap.price if low_snap else 0)
            high_val = agg["high"] or 0
            avg_val = round(agg["avg"] or 0)
        out[d_iso] = {
            "date": d_iso,
            "low_price": low_val,
            "high_price": high_val,
            "avg_price": avg_val,
            "min_price_url": low_snap.url if low_snap else "",
            "all_prices": all_prices if d == today else [],
        }

    return sorted(out.values(), key=lambda x: x["date"])


def get_all_daily_summary(category: str | None = None):
    """
    Return list of { date, keyword_name, keyword_id, low_price, high_price, avg_price, min_price_url }
    combining DailyPriceSummary + DailyPriceSnapshot, newest date first.
    """
    out = {}  # key: (keyword_id, date_iso)

    # --- Historical from DailyPriceSummary ---
    qs = DailyPriceSummary.objects
    if category:
        qs = qs.filter(category=category)
    for s in qs.order_by("-date", "keyword_name"):
        key = (s.keyword_id, s.date.isoformat())
        out[key] = {
            "date": s.date.isoformat(),
            "keyword_id": s.keyword_id,
            "keyword_name": s.keyword_name,
            "low_price": s.low_price,
            "high_price": s.high_price,
            "avg_price": s.avg_price,
            "min_price_url": s.min_price_url,
        }

    # --- Today's snapshots from DailyPriceSnapshot ---
    snap_qs = DailyPriceSnapshot.objects
    if category:
        snap_qs = snap_qs.filter(keyword__category=category)
    for row in (
        snap_qs.values("keyword", "date")
        .annotate(low_price=Min("price"), high_price=Max("price"), avg_price=Avg("price"))
        .order_by("-date", "keyword__name")
    ):
        kw = Keyword.objects.filter(pk=row["keyword"]).first()
        if not kw:
            continue
        low_url = (
            DailyPriceSnapshot.objects.filter(keyword_id=row["keyword"], date=row["date"])
            .order_by("price")
            .values_list("url", flat=True)
            .first()
        ) or ""
        key = (row["keyword"], row["date"].isoformat())
        out[key] = {
            "date": row["date"].isoformat(),
            "keyword_id": row["keyword"],
            "keyword_name": kw.name,
            "low_price": row["low_price"],
            "high_price": row["high_price"],
            "avg_price": round(row["avg_price"] or 0),
            "min_price_url": low_url,
        }

    return sorted(out.values(), key=lambda x: x["date"], reverse=True)


def get_available_dates():
    """Return list of distinct snapshot dates (iso format), newest first, from both tables."""
    dates = set()
    for d in DailyPriceSnapshot.objects.values_list("date", flat=True).distinct():
        dates.add(d.isoformat())
    for d in DailyPriceSummary.objects.values_list("date", flat=True).distinct():
        dates.add(d.isoformat())
    return sorted(dates, reverse=True)


def get_daily_prices(date):
    """
    Return every price record for the given date from DailyPriceSnapshot.
    For historical dates (only in DailyPriceSummary), returns the summary row as a single record.
    """
    if isinstance(date, str):
        try:
            date = date_type.fromisoformat(date)
        except ValueError:
            return []

    # Try raw snapshots first
    snapshots = DailyPriceSnapshot.objects.filter(date=date).order_by("keyword_name", "price")
    if snapshots.exists():
        return [
            {
                "keyword_name": s.keyword_name or "",
                "price": s.price,
                "product_name": (s.product_name or "")[:200],
                "url": s.url or "",
            }
            for s in snapshots
        ]

    # Fall back to summary rows (historical date — no individual records kept)
    return [
        {
            "keyword_name": s.keyword_name or "",
            "price": s.low_price,
            "product_name": f"(历史归档) 最低 ¥{s.low_price:,} / 平均 ¥{s.avg_price:,} / 最高 ¥{s.high_price:,}",
            "url": s.min_price_url or "",
        }
        for s in DailyPriceSummary.objects.filter(date=date).order_by("keyword_name")
    ]


def get_keywords_with_summary(category: str | None = None):
    """Return list of keywords with latest low_price and date if any. Optional category filter."""
    qs = Keyword.objects.all()
    if category:
        qs = qs.filter(category=category)
    result = []
    for kw in qs:
        # Check DailyPriceSnapshot first (today's data is fresher)
        latest_snap = (
            DailyPriceSnapshot.objects.filter(keyword=kw)
            .order_by("-date", "price")
            .first()
        )
        latest_sum = (
            DailyPriceSummary.objects.filter(keyword=kw)
            .order_by("-date")
            .first()
        )
        # Pick whichever is more recent
        if latest_snap and latest_sum:
            if latest_snap.date >= latest_sum.date:
                latest_date = latest_snap.date.isoformat()
                latest_price = latest_snap.price
            else:
                latest_date = latest_sum.date.isoformat()
                latest_price = latest_sum.low_price
        elif latest_snap:
            latest_date = latest_snap.date.isoformat()
            latest_price = latest_snap.price
        elif latest_sum:
            latest_date = latest_sum.date.isoformat()
            latest_price = latest_sum.low_price
        else:
            latest_date = None
            latest_price = None
        result.append({
            "id": kw.id,
            "name": kw.name,
            "latest_date": latest_date,
            "latest_low_price": latest_price,
        })
    return result
