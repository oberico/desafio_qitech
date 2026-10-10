import os

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "transferencias")

DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
BANK_API_URL = os.environ.get("BANK_API_URL", "http://localhost:8001")

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")

BYPASS_ENDPOINTS = ["/", "/health_check"]
INTERNAL_ROUTE_PREFIX = "/internal/"
