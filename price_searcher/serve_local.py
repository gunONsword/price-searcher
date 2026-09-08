import os
os.environ["DJANGO_SETTINGS_MODULE"] = "deployment_settings"
from django.core.wsgi import get_wsgi_application
from waitress import serve
if __name__ == "__main__":
    serve(get_wsgi_application(), host="127.0.0.1", port=8001, threads=8,
          trusted_proxy="127.0.0.1", trusted_proxy_headers={"x-forwarded-proto"})
