"""Open the hardware dashboard directly on the local deployment domain."""
from django.urls import path
from django.views.generic import RedirectView
from price_searcher.urls import urlpatterns as application_urls

urlpatterns = [path('', RedirectView.as_view(url='/dashboard/', permanent=False))] + application_urls
