import os

from constants import SCHEMAS_DIR
from utils.schema_handler import validate_json

POST_LEDGER_TRANSACTION_SCHEMA = os.path.join(SCHEMAS_DIR, "post_ledger_transaction.json")


class LedgerController:
    def create_transaction(self, payload: dict) -> dict:
        validate_json(payload, POST_LEDGER_TRANSACTION_SCHEMA)
        return payload
    