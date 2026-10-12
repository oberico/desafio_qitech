import os
from datetime import datetime, timedelta

from connectors import BankConnector
from constants import RECEIPT_KEY_PREFIX, RECEIPT_ORPHAN_GRACE_HOURS, SCHEMAS_DIR
from controllers.base_controller import BaseController
from errors import BankRefused, BankUnavailable
from repositories import PaymentRepository
from utils.as_of import resolve_as_of
from utils.schema_handler import validate_json

POST_RECEIPT_RECONCILE_SCHEMA = os.path.join(SCHEMAS_DIR, "post_receipt_reconcile.json")
ORPHAN_REFUND_KEY_PREFIX = "orphan-refund:"


class ReceiptReconcileController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)
        self.bank_connector = BankConnector()

    def run(self, payload: dict) -> dict:
        payload = payload or {}
        validate_json(payload, POST_RECEIPT_RECONCILE_SCHEMA)
        as_of = resolve_as_of(payload)
        cutoff = as_of - timedelta(hours=RECEIPT_ORPHAN_GRACE_HOURS)

        refunded, deferred = [], []
        for orphan in self._orphans(cutoff):
            (refunded if self._refund(orphan) else deferred).append(orphan["transaction_key"])

        return {"as_of": as_of.isoformat(), "refunded": refunded, "deferred": deferred}

    def _orphans(self, cutoff: datetime):
        cursor = None
        while True:
            page = self.bank_connector.list_open_receipts(cutoff.isoformat(), cursor)
            receipts = [receipt for receipt in page["data"] if receipt["idempotency_key"].startswith(RECEIPT_KEY_PREFIX)]
            known = self.payment_repository.existing_transaction_keys([receipt["transaction_key"] for receipt in receipts])
            self.session.rollback()
            yield from (receipt for receipt in receipts if receipt["transaction_key"] not in known)
            if page["is_last_page"]:
                return
            cursor = page["cursor"]

    def _refund(self, orphan: dict) -> bool:
        refund = {
            "type": "refund",
            "reverses_transaction_key": orphan["transaction_key"],
            "entries": [
                {"account_code": "in_transit", "debit_minor": orphan["amount_minor"]},
                {"account_code": "reserves", "credit_minor": orphan["amount_minor"]},
            ],
        }
        try:
            self.bank_connector.post_ledger_transaction(
                refund, f"{ORPHAN_REFUND_KEY_PREFIX}{orphan['transaction_key']}", forward_refusals=True
            )
        except (BankRefused, BankUnavailable):
            return False
        return True
