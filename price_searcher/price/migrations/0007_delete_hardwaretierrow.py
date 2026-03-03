from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0006_dailypricesummary_add_site"),
    ]

    operations = [
        migrations.DeleteModel(
            name="HardwareTierRow",
        ),
    ]
