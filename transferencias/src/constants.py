import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://rnv:rnv@localhost:5433/transferencias")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")
BANK_API_URL = os.environ.get("BANK_API_URL", "http://localhost:8001")

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")
