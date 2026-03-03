import os
import tempfile
import threading
import time
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import DailyPriceSnapshot, Keyword
from .services.daily_stats import (
    get_daily_stats,
    get_all_daily_summary,
    get_available_dates,
    get_daily_prices,
    get_keywords_with_summary,
    archive_and_purge_old_snapshots,
)
from .services.price_search import search_products, _get_rakuten_app_id

# Shared state for collect progress (updated by background thread)
_collect_progress = {"running": False, "total": 0, "current": 0, "keyword": "", "error": None, "skipped": []}
_progress_lock = threading.Lock()
# When set, only these keyword names are collected (order preserved). None = all.
_collect_keywords_filter = None


def _run_collect_thread():
    """Run collection in thread; update _collect_progress after each keyword."""
    global _collect_progress
    today = date.today()
    if _collect_keywords_filter:
        name_to_kw = {kw.name: kw for kw in Keyword.objects.all()}
        keywords = [name_to_kw[n] for n in _collect_keywords_filter if n in name_to_kw]
    else:
        keywords = list(Keyword.objects.all())
    if not keywords:
        with _progress_lock:
            _collect_progress["running"] = False
            _collect_progress["error"] = "No keywords in DB"
        return
    if not _get_rakuten_app_id():
        with _progress_lock:
            _collect_progress["running"] = False
            _collect_progress["error"] = "RAKUTEN_APP_ID not set"
        return

    # Archive yesterday-and-older snapshots into DailyPriceSummary, then purge them
    try:
        archived_days, deleted_rows = archive_and_purge_old_snapshots()
        if deleted_rows:
            print(f"[Collect] Archived {archived_days} day(s), purged {deleted_rows} old snapshot rows.")
    except Exception as arch_err:
        print(f"[Collect] Archive step failed (non-fatal): {arch_err}")

    with _progress_lock:
        _collect_progress["total"] = len(keywords)
        _collect_progress["current"] = 0
        _collect_progress["keyword"] = ""
        _collect_progress["error"] = None
        _collect_progress["skipped"] = []
    for i, kw in enumerate(keywords):
        if i > 0:
            time.sleep(1)
        with _progress_lock:
            _collect_progress["current"] = i + 1
            _collect_progress["keyword"] = kw.name
        min_price = getattr(kw, "min_price", 20000) or 20000
        try:
            data = search_products(kw.name, min_price=min_price)
        except Exception as e:
            with _progress_lock:
                _collect_progress["skipped"].append({"keyword": kw.name, "error": str(e)})
            continue
        results = data.get("results", [])
        if not results:
            with _progress_lock:
                _collect_progress["skipped"].append({"keyword": kw.name, "error": "0 results from API"})
            continue
        # Double-check min_price filter
        filtered = [r for r in results if (r.get("price") or 0) >= min_price]
        for r in filtered:
            url = (r.get("url") or "")[:1000]
            if not url or DailyPriceSnapshot.objects.filter(keyword=kw, date=today, url=url).exists():
                continue
            min_price_val = getattr(kw, "min_price", 20000) or 20000
            DailyPriceSnapshot.objects.create(
                keyword=kw,
                date=today,
                keyword_name=kw.name,
                category=kw.category,
                min_search_price=min_price_val,
                site=r.get("site", ""),
                product_name=(r.get("name") or "")[:500],
                price=r.get("price", 0),
                url=url,
            )
    with _progress_lock:
        _collect_progress["running"] = False
        _collect_progress["keyword"] = ""


@api_view(["GET"])
def search_api(request):
    keyword = request.GET.get("q", "")
    data = search_products(keyword)
    return Response(data)


@api_view(["GET"])
def keywords_api(request):
    """List tracked keywords with latest low price and date."""
    data = get_keywords_with_summary()
    return Response(data)


@api_view(["GET"])
def daily_stats_api(request):
    """Daily low/avg price and min-price URL for chart and table. Query: keyword=xxx or keyword_id=123."""
    keyword = request.GET.get("keyword", "").strip()
    keyword_id = request.GET.get("keyword_id", "")
    try:
        keyword_id = int(keyword_id) if keyword_id else None
    except ValueError:
        keyword_id = None
    stats = get_daily_stats(keyword_name=keyword or None, keyword_id=keyword_id)
    return Response({"keyword": keyword or (stats and "unknown") or "", "daily": stats})


@api_view(["GET"])
def dashboard_stats_api(request):
    """All keywords × dates: low, high, avg, min_price_url; plus available dates. Optional ?category=gpu|cpu|ram|ssd|motherboard."""
    category = (request.GET.get("category") or "").strip().lower() or None
    if category and category not in ("gpu", "cpu", "ram", "ssd", "motherboard"):
        category = None
    summary = get_all_daily_summary(category=category)
    keywords = get_keywords_with_summary(category=category)
    dates = get_available_dates()
    return Response({"summary": summary, "keywords": keywords, "dates": dates, "category": category or "gpu"})


@api_view(["GET"])
def daily_prices_api(request):
    """Every price record for one day (for distribution chart and price list). Query: date=YYYY-MM-DD."""
    date_str = request.GET.get("date", "").strip()
    if not date_str:
        return Response({"prices": [], "date": None})
    prices = get_daily_prices(date_str)
    return Response({"date": date_str, "prices": prices})


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def seed_gpu_keywords_api(request):
    """Run seed_gpu_keywords (add preset GPU keywords including RTX 50 series). Idempotent."""
    from io import StringIO
    out = StringIO()
    try:
        call_command("seed_gpu_keywords", stdout=out)
        return Response({"ok": True, "message": "预设关键词已添加", "log": out.getvalue()})
    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def seed_other_hardware_keywords_api(request):
    """Seed keywords for CPU/RAM/SSD/Motherboard. Body: {"category": "cpu"|"ram"|"ssd"|"motherboard"}."""
    try:
        body = request.data if hasattr(request, "data") and request.data else {}
        if not body and getattr(request, "body", None):
            import json
            body = json.loads((request.body or b"{}").decode("utf-8"))
    except Exception:
        body = {}
    category = (body.get("category") or "").strip().lower()
    if category not in ("cpu", "ram", "ssd", "motherboard"):
        return Response({"ok": False, "error": "Missing or invalid category (use: cpu, ram, ssd, motherboard)"}, status=400)
    from io import StringIO
    out = StringIO()
    try:
        call_command("seed_other_hardware_keywords", "--category=" + category, stdout=out)
        return Response({"ok": True, "message": f"已添加 {category} 预设关键词", "log": out.getvalue()})
    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=500)


@api_view(["GET"])
def collect_progress_api(request):
    """Current collect progress: total, current, keyword, running. Poll every 1s."""
    with _progress_lock:
        out = dict(_collect_progress)
    return Response(out)


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def run_collect_daily_prices_api(request):
    """Start collect in background. Body: optional {"keywords": ["RTX 5060", ...]}. Only checked keywords are collected."""
    global _collect_keywords_filter
    try:
        body = request.data if hasattr(request, "data") and request.data else {}
        if not body and getattr(request, "body", None):
            import json
            body = json.loads((request.body or b"{}").decode("utf-8"))
    except Exception:
        body = {}
    keyword_names = body.get("keywords")
    if isinstance(keyword_names, list) and len(keyword_names) > 0:
        _collect_keywords_filter = [str(n).strip() for n in keyword_names if str(n).strip()]
    else:
        _collect_keywords_filter = None

    with _progress_lock:
        if _collect_progress["running"]:
            return Response({"ok": False, "error": "采集正在进行中"}, status=409)
        _collect_progress["running"] = True
        _collect_progress["total"] = 0
        _collect_progress["current"] = 0
        _collect_progress["keyword"] = ""
        _collect_progress["error"] = None
        _collect_progress["skipped"] = []
    total = len(_collect_keywords_filter) if _collect_keywords_filter else Keyword.objects.count()
    thread = threading.Thread(target=_run_collect_thread)
    thread.daemon = True
    thread.start()
    return Response({"ok": True, "total": total})


def dashboard(request):
    """Visualization: daily price trends (all GPUs) and table of min/max/avg per GPU per day."""
    return render(request, "price/dashboard.html")


def _get_export_key():
    return (os.getenv("EXPORT_DATA_KEY") or "").strip()


def _get_import_key():
    return (os.getenv("IMPORT_DATA_KEY") or "").strip()


@require_http_methods(["GET"])
def export_data_view(request):
    """
    Export DB as JSON (dumpdata) for migration. No shell needed.
    Usage: open in browser with ?key=YOUR_EXPORT_DATA_KEY (set in .env).
    Returns data.json as download.
    """
    key = (request.GET.get("key") or "").strip()
    expected = _get_export_key()
    if not expected or key != expected:
        return HttpResponse("Missing or invalid key. Set EXPORT_DATA_KEY in .env and use ?key=...", status=403)
    out = StringIO()
    try:
        call_command(
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            "-e", "contenttypes",
            "-e", "auth.Permission",
            stdout=out,
        )
        data = out.getvalue()
    except Exception as e:
        return HttpResponse(f"Export failed: {e}", status=500)
    resp = HttpResponse(data, content_type="application/json")
    resp["Content-Disposition"] = 'attachment; filename="data.json"'
    return resp


@csrf_exempt
@require_http_methods(["GET", "POST"])
def import_data_view(request):
    """
    Run migrate + loaddata from uploaded JSON. No shell needed.
    GET: show form (key + file). POST: key + file -> migrate then loaddata.
    Set IMPORT_DATA_KEY in .env on Render and use the same key when submitting.
    """
    expected = _get_import_key()
    if not expected:
        return HttpResponse(
            "Import disabled: set IMPORT_DATA_KEY in environment (e.g. on Render).",
            status=403,
        )
    if request.method == "GET":
        html = """
        <!DOCTYPE html><html><head><meta charset="utf-8"><title>Import data</title></head><body>
        <h2>Import data to this database (migrate + loaddata)</h2>
        <p>Set IMPORT_DATA_KEY in env and use the same key below. Use the data.json from export.</p>
        <form method="post" enctype="multipart/form-data">
          <label>Key: <input name="key" type="text" required /></label><br/><br/>
          <label>File (data.json): <input name="file" type="file" accept=".json" required /></label><br/><br/>
          <button type="submit">Run migrate and import</button>
        </form>
        </body></html>
        """
        return HttpResponse(html)
    key = (request.POST.get("key") or "").strip()
    if key != expected:
        return HttpResponse("Invalid key.", status=403)
    f = request.FILES.get("file")
    if not f:
        return HttpResponse("No file uploaded.", status=400)
    suffix = ".json"
    with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
        for chunk in f.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    try:
        out = StringIO()
        err = StringIO()
        call_command("migrate", "--noinput", stdout=out, stderr=err)
        migrate_log = out.getvalue() + err.getvalue()
        out = StringIO()
        err = StringIO()
        call_command("loaddata", tmp_path, stdout=out, stderr=err)
        load_log = out.getvalue() + err.getvalue()
        return HttpResponse(
            f"<pre>Migrate:\n{migrate_log}\n\nLoaddata:\n{load_log}</pre><p>Done.</p>",
            content_type="text/html; charset=utf-8",
        )
    except Exception as e:
        return HttpResponse(f"<pre>Import failed: {e}</pre>", status=500)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
