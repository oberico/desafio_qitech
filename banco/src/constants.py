import os

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "banco")
BUSINESS_TIMEZONE = "America/Sao_Paulo"

DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
TRANSFERENCIAS_API_URL = os.environ.get("TRANSFERENCIAS_API_URL", "http://localhost:8002")
TRANSFERENCIAS_TIMEOUT_SECONDS = float(os.environ.get("TRANSFERENCIAS_TIMEOUT_SECONDS", "5"))

BYPASS_ENDPOINTS = ["/", "/health_check"]
INTERNAL_ROUTE_PREFIXES = ("/internal/", "/ledger/", "/auth/")
PUBLIC_ROUTES = {("GET", "/"), ("GET", "/health_check"), ("POST", "/clients")}

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")
