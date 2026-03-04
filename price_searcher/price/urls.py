from django.urls import path
from .views import (
    search_api,
    keywords_api,
    daily_stats_api,
    dashboard_stats_api,
    daily_prices_api,
    collect_progress_api,
    seed_gpu_keywords_api,
    seed_other_hardware_keywords_api,
    run_collect_daily_prices_api,
    dashboard,
    export_data_view,
    import_data_view,
    keywords_manage_api,
    keyword_detail_api,
)

urlpatterns = [
    path("search/", search_api),
    path("keywords/", keywords_api),
    path("daily-stats/", daily_stats_api),
    path("dashboard-stats/", dashboard_stats_api),
    path("daily-prices/", daily_prices_api),
    path("collect-progress/", collect_progress_api),
    path("seed-gpu-keywords/", seed_gpu_keywords_api),
    path("seed-other-hardware-keywords/", seed_other_hardware_keywords_api),
    path("run-collect-daily-prices/", run_collect_daily_prices_api),
    path("dashboard/", dashboard),
    path("tools/export-data/", export_data_view),
    path("tools/import-data/", import_data_view),
    path("keywords-manage/", keywords_manage_api),
    path("keywords-manage/<int:pk>/", keyword_detail_api),
]
