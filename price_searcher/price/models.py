from django.db import models


class Keyword(models.Model):
    """Tracked search keyword for computer parts (e.g. RTX 4070, CPU, RAM)."""
    CATEGORY_GPU = "gpu"
    CATEGORY_CPU = "cpu"
    CATEGORY_MOTHERBOARD = "motherboard"
    CATEGORY_RAM = "ram"
    CATEGORY_SSD = "ssd"
    CATEGORY_CHOICES = [
        (CATEGORY_GPU, "GPU"),
        (CATEGORY_CPU, "CPU"),
        (CATEGORY_MOTHERBOARD, "Motherboard"),
        (CATEGORY_RAM, "RAM"),
        (CATEGORY_SSD, "SSD"),
    ]
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GPU,
        db_index=True,
        help_text="Hardware category for filtering and display",
    )
    # Minimum price (JPY) to accept when collecting; results below this are ignored. Default 20000.
    min_price = models.PositiveIntegerField(default=20000, help_text="Only save prices >= this (JPY)")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name



class DailyPriceSnapshot(models.Model):
    """
    One row per product result per day. Keyword main fields are denormalized here
    so each snapshot is self-contained (keyword name, category, min_search_price).
    """
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="snapshots")
    date = models.DateField(db_index=True)
    # Denormalized from Keyword for quick filtering/display without join
    keyword_name = models.CharField(max_length=200, db_index=True, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Keyword.CATEGORY_CHOICES,
        default=Keyword.CATEGORY_GPU,
        db_index=True,
        blank=True,
    )
    # Minimum price (JPY) used when collecting; only results >= this were saved.
    min_search_price = models.PositiveIntegerField(
        default=20000,
        help_text="Keyword's min_price at collection time (JPY)",
    )
    site = models.CharField(max_length=50)
    product_name = models.CharField(max_length=500)
    price = models.PositiveIntegerField()
    url = models.URLField(max_length=1000)

    class Meta:
        ordering = ["-date", "price"]
        indexes = [
            models.Index(fields=["keyword", "date"]),
            models.Index(fields=["keyword_name", "date"]),
        ]

    def __str__(self):
        return f"{self.keyword_name or self.keyword.name} | {self.date} | {self.site} | {self.price}"


class DailyPriceSummary(models.Model):
    """
    Archived daily aggregate per (keyword, date, site): one row per platform per day.
    Populated automatically when collection starts — raw DailyPriceSnapshot rows
    from previous days are summarised here, then deleted to keep the snapshot
    table lean (today-only).
    """
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="daily_summaries")
    date = models.DateField(db_index=True)
    keyword_name = models.CharField(max_length=200, db_index=True, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Keyword.CATEGORY_CHOICES,
        default=Keyword.CATEGORY_GPU,
        db_index=True,
        blank=True,
    )
    site = models.CharField(max_length=50, default="Rakuten", db_index=True)
    low_price = models.PositiveIntegerField()
    high_price = models.PositiveIntegerField()
    avg_price = models.PositiveIntegerField()
    min_price_url = models.URLField(max_length=1000, blank=True)

    class Meta:
        unique_together = [["keyword", "date", "site"]]
        ordering = ["-date", "keyword_name", "site"]
        indexes = [
            models.Index(fields=["keyword_name", "date"]),
            models.Index(fields=["category", "date"]),
        ]

    def __str__(self):
        return f"{self.keyword_name} | {self.date} | {self.site} | low={self.low_price}"
