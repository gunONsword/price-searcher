# Generated manually for Keyword category and HardwareTierRow

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0002_add_keyword_min_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="category",
            field=models.CharField(
                choices=[
                    ("gpu", "GPU"),
                    ("cpu", "CPU"),
                    ("motherboard", "Motherboard"),
                    ("ram", "RAM"),
                    ("ssd", "SSD"),
                ],
                db_index=True,
                default="gpu",
                help_text="Hardware category for filtering and display",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="keyword",
            options={"ordering": ["category", "name"]},
        ),
        migrations.CreateModel(
            name="HardwareTierRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("cpu", "CPU"),
                            ("motherboard", "Motherboard"),
                            ("ram", "RAM"),
                            ("ssd", "SSD"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("entry", "入门"),
                            ("value", "性价比"),
                            ("mid", "中端"),
                            ("mid_high", "中高端"),
                            ("high", "高端"),
                            ("enthusiast", "发烧级"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0, help_text="Display order within category")),
                ("col1_name", models.CharField(blank=True, max_length=100)),
                ("col1_value", models.CharField(blank=True, max_length=500)),
                ("col2_name", models.CharField(blank=True, max_length=100)),
                ("col2_value", models.CharField(blank=True, max_length=500)),
            ],
            options={
                "ordering": ["category", "sort_order"],
                "unique_together": {("category", "tier")},
            },
        ),
    ]
