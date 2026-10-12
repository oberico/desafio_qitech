import os

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "transferencias")

DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
BANK_API_URL = os.environ.get("BANK_API_URL", "http://localhost:8001")
BANK_TIMEOUT_SECONDS = float(os.environ.get("BANK_TIMEOUT_SECONDS", "5"))
INTERBANK_API_URL = os.environ.get("INTERBANK_API_URL", "http://localhost:8003")
INTERBANK_TIMEOUT_SECONDS = float(os.environ.get("INTERBANK_TIMEOUT_SECONDS", "5"))

PAYOUT_MAX_ATTEMPTS = int(os.environ.get("PAYOUT_MAX_ATTEMPTS", "3"))
PAYOUT_BACKOFF_BASE_SECONDS = int(os.environ.get("PAYOUT_BACKOFF_BASE_SECONDS", "60"))
PAYOUT_MAX_PER_RUN = int(os.environ.get("PAYOUT_MAX_PER_RUN", "50"))

DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT_SECONDS = float(os.environ.get("DB_POOL_TIMEOUT_SECONDS", "3"))

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")

BYPASS_ENDPOINTS = ["/", "/health_check"]
INTERNAL_ROUTE_PREFIX = "/internal/"
