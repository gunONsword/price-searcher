"""Local HTTPS deployment through Cloudflare Tunnel."""
from price_searcher.settings import *
from pathlib import Path
DEBUG = False
ROOT_URLCONF = "deployment_urls"
ALLOWED_HOSTS = ["hardware-price.gunonsword-ai.com", "127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = ["https://hardware-price.gunonsword-ai.com"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECRET_KEY = (Path(r"C:/Users/gos/project/price_searcher") / ".local" / "django-secret.txt").read_text().strip()
STATIC_ROOT = BASE_DIR / "staticfiles"
MIDDLEWARE = list(MIDDLEWARE)
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
