import os

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "banco")

INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")

BYPASS_ENDPOINTS = ["/", "/health_check"]
INTERNAL_ROUTE_PREFIXES = ("/internal/", "/ledger/", "/auth/")
