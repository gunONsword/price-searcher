from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0005_dailypricesummary"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailypricesummary",
            name="site",
            field=models.CharField(db_index=True, default="Rakuten", max_length=50),
        ),
        # Replace old (keyword, date) unique constraint with (keyword, date, site)
        migrations.RemoveConstraint(
            model_name="dailypricesummary",
            name="unique_keyword_date_summary",
        ),
        migrations.AddConstraint(
            model_name="dailypricesummary",
            constraint=models.UniqueConstraint(
                fields=["keyword", "date", "site"],
                name="unique_keyword_date_site_summary",
            ),
        ),
        migrations.AlterModelOptions(
            name="dailypricesummary",
            options={"ordering": ["-date", "keyword_name", "site"]},
        ),
    ]
