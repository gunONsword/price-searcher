"""
Collect today's prices for tracked keywords and save to DailyPriceSnapshot.
Run daily via cron, e.g.: 0 9 * * * cd /path && python manage.py collect_daily_prices
Respects Rakuten 2 QPS limit by waiting 1s between keywords.
"""
import time
from datetime import date

from django.core.management.base import BaseCommand

from price.models import DailyPriceSnapshot, Keyword
from price.services.price_search import search_products, _get_rakuten_app_id


class Command(BaseCommand):
    help = "Fetch prices for all tracked keywords and save daily snapshots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keyword",
            type=str,
            help="Run only for this keyword (default: all keywords).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only fetch and print, do not save to DB.",
        )

    def handle(self, *args, **options):
        today = date.today()
        keyword_name = options.get("keyword")
        dry_run = options.get("dry_run", False)

        if keyword_name:
            keywords = Keyword.objects.filter(name=keyword_name)
            if not keywords.exists():
                self.stdout.write(self.style.WARNING(f"Keyword not found: {keyword_name}"))
                return
        else:
            keywords = Keyword.objects.all()
            if not keywords.exists():
                self.stdout.write(self.style.WARNING("No keywords in DB. Add some in admin or shell."))
                return

        app_id = _get_rakuten_app_id()
        if not app_id:
            self.stdout.write(self.style.ERROR("RAKUTEN_APP_ID is not set. Add it to .env in the project directory."))
            return
        self.stdout.write(f"Using RAKUTEN_APP_ID: {app_id[:8]}...{app_id[-4:] if len(app_id) > 12 else '***'}")

        for i, kw in enumerate(keywords):
            if i > 0:
                time.sleep(1)
            min_price = getattr(kw, "min_price", 20000) or 20000
            self.stdout.write(f"Fetching: {kw.name} (minPrice={min_price}) ...")
            try:
                data = search_products(kw.name, min_price=min_price)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Skip ({kw.name}): {e}"))
                err_str = str(e).lower()
                if "403" in err_str and "referrer" in err_str:
                    self.stdout.write(self.style.ERROR(
                        "    Hint: In Rakuten app settings, add allowed Referer/Origin."
                    ))
                elif "wrong_parameter" in err_str:
                    self.stdout.write(self.style.ERROR(
                        "    Hint: This keyword may be rejected by API (e.g. 'RTX 4090 D'). Try removing space or use legacy API."
                    ))
                continue
            results = data.get("results", [])
            if not results:
                self.stdout.write(self.style.WARNING(f"  No results for {kw.name}"))
                continue

            if dry_run:
                for r in results[:5]:
                    self.stdout.write(f"  {r.get('site')} | {r.get('price')} | {r.get('url', '')[:50]}...")
                self.stdout.write(f"  Total: {len(results)} items")
                continue

            # Double-check min_price filter (API already filters, but ensure consistency)
            filtered = [r for r in results if (r.get("price") or 0) >= min_price]

            # Only store non-duplicate: same (keyword, date, url) = same record, skip
            created = 0
            for r in filtered:
                url = (r.get("url") or "")[:1000]
                if not url or DailyPriceSnapshot.objects.filter(keyword=kw, date=today, url=url).exists():
                    continue
                DailyPriceSnapshot.objects.create(
                    keyword=kw,
                    date=today,
                    keyword_name=kw.name,
                    category=kw.category,
                    min_search_price=min_price,
                    site=r.get("site", ""),
                    product_name=(r.get("name") or "")[:500],
                    price=r.get("price", 0),
                    url=url,
                )
                created += 1

            self.stdout.write(self.style.SUCCESS(f"  Saved {created} snapshots for {kw.name} on {today}"))
