"""
One-time backfill: read all existing DailyPriceSnapshot rows and write
aggregated summaries into DailyPriceSummary (low / avg / high per keyword+date+site).

Existing DailyPriceSnapshot data is NOT deleted — run this before the first
real collect-and-purge cycle to preserve historical records you already have.

Usage:
    python manage.py backfill_daily_summary
    python manage.py backfill_daily_summary --dry-run   # preview only
"""
from django.core.management.base import BaseCommand

from price.models import DailyPriceSnapshot
from price.services.daily_stats import _upsert_summary_from_snapshots


class Command(BaseCommand):
    help = "Backfill DailyPriceSummary from all existing DailyPriceSnapshot rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be written without actually writing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total_snaps = DailyPriceSnapshot.objects.count()
        self.stdout.write(f"DailyPriceSnapshot total rows: {total_snaps}")

        if dry_run:
            from django.db.models import Min, Max, Avg
            groups = list(
                DailyPriceSnapshot.objects.values("keyword_id", "date", "site").distinct()
            )
            self.stdout.write(f"Would write {len(groups)} summary row(s):")
            for g in groups:
                rows = DailyPriceSnapshot.objects.filter(
                    keyword_id=g["keyword_id"], date=g["date"], site=g["site"]
                )
                agg = rows.aggregate(low=Min("price"), high=Max("price"), avg=Avg("price"))
                kw_name = rows.first().keyword_name or str(g["keyword_id"])
                self.stdout.write(
                    f"  {kw_name} | {g['date']} | {g['site']} | "
                    f"low={agg['low']} avg={round(agg['avg'] or 0)} high={agg['high']}"
                )
            return

        written = _upsert_summary_from_snapshots(DailyPriceSnapshot.objects.all())
        self.stdout.write(self.style.SUCCESS(
            f"Done. Written/updated {written} DailyPriceSummary row(s)."
        ))
