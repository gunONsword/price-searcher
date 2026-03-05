from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0008_remove_dailypricesummary_unique_keyword_date_site_summary_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="guide_price",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="User's reference/guide price (JPY)",
            ),
        ),
    ]
