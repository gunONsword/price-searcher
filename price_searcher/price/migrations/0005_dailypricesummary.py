from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0004_dailypricesnapshot_keyword_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyPriceSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_summaries", to="price.keyword")),
                ("date", models.DateField(db_index=True)),
                ("keyword_name", models.CharField(blank=True, db_index=True, max_length=200)),
                ("category", models.CharField(
                    blank=True, db_index=True, default="gpu", max_length=20,
                    choices=[("gpu","GPU"),("cpu","CPU"),("motherboard","Motherboard"),("ram","RAM"),("ssd","SSD")],
                )),
                ("low_price", models.PositiveIntegerField()),
                ("high_price", models.PositiveIntegerField()),
                ("avg_price", models.PositiveIntegerField()),
                ("min_price_url", models.URLField(blank=True, max_length=1000)),
            ],
            options={"ordering": ["-date", "keyword_name"]},
        ),
        migrations.AddConstraint(
            model_name="dailypricesummary",
            constraint=models.UniqueConstraint(fields=["keyword", "date"], name="unique_keyword_date_summary"),
        ),
        migrations.AddIndex(
            model_name="dailypricesummary",
            index=models.Index(fields=["keyword_name", "date"], name="price_summary_kw_date_idx"),
        ),
        migrations.AddIndex(
            model_name="dailypricesummary",
            index=models.Index(fields=["category", "date"], name="price_summary_cat_date_idx"),
        ),
    ]
