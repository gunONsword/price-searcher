from django.contrib import admin
from .models import Keyword, DailyPriceSnapshot, DailyPriceSummary


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "min_price"]
    list_filter = ["category"]
    search_fields = ["name"]


@admin.register(DailyPriceSnapshot)
class DailyPriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["keyword_name", "category", "date", "site", "price", "min_search_price", "product_name"]
    list_filter = ["category", "date", "site"]
    search_fields = ["product_name", "keyword_name", "keyword__name"]
    date_hierarchy = "date"


@admin.register(DailyPriceSummary)
class DailyPriceSummaryAdmin(admin.ModelAdmin):
    list_display = ["keyword_name", "category", "date", "low_price", "avg_price", "high_price"]
    list_filter = ["category", "date"]
    search_fields = ["keyword_name", "keyword__name"]
    date_hierarchy = "date"
    readonly_fields = ["keyword", "date", "keyword_name", "category", "low_price", "avg_price", "high_price", "min_price_url"]
