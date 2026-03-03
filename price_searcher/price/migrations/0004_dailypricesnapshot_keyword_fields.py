# Add Keyword main fields to DailyPriceSnapshot (denormalized) and min_search_price

from django.db import migrations, models


def backfill_keyword_fields(apps, schema_editor):
    DailyPriceSnapshot = apps.get_model("price", "DailyPriceSnapshot")
    for row in DailyPriceSnapshot.objects.select_related("keyword"):
        row.keyword_name = row.keyword.name
        row.category = row.keyword.category
        row.min_search_price = getattr(row.keyword, "min_price", 20000) or 20000
        row.save(update_fields=["keyword_name", "category", "min_search_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0003_add_keyword_category_and_hardware_tier"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailypricesnapshot",
            name="keyword_name",
            field=models.CharField(blank=True, db_index=True, max_length=200),
        ),
        migrations.AddField(
            model_name="dailypricesnapshot",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("gpu", "GPU"),
                    ("cpu", "CPU"),
                    ("motherboard", "Motherboard"),
                    ("ram", "RAM"),
                    ("ssd", "SSD"),
                ],
                db_index=True,
                default="gpu",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="dailypricesnapshot",
            name="min_search_price",
            field=models.PositiveIntegerField(
                default=20000,
                help_text="Keyword's min_price at collection time (JPY)",
            ),
        ),
        migrations.RunPython(backfill_keyword_fields, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="dailypricesnapshot",
            index=models.Index(fields=["keyword_name", "date"], name="price_daily_keyword_ki_idx"),
        ),
    ]
