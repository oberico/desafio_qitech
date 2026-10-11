import os

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "banco")
BUSINESS_TIMEZONE = "America/Sao_Paulo"

DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

BYPASS_ENDPOINTS = ["/", "/health_check"]
INTERNAL_ROUTE_PREFIXES = ("/internal/", "/ledger/", "/auth/")
ADMIN_ROUTE_PREFIX = "/admin/"
PUBLIC_ROUTES = {("GET", "/"), ("GET", "/health_check"), ("POST", "/clients")}

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")
