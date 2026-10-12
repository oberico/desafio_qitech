from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from tests.utils.receipt_reconcile_requests import ReceiptReconcileRequests

GRACE_HOURS = 24


@pytest.fixture(scope="session")
def receipt_reconcile(api_url, internal_token) -> ReceiptReconcileRequests:
    return ReceiptReconcileRequests(api_url, internal_token)


def hours_from_now(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def after_the_grace() -> str:
    return hours_from_now(GRACE_HOURS + 1)


def receipt_entries(amount_minor: int) -> dict:
    return {
        "type": "receipt",
        "entries": [
            {"account_code": "reserves", "debit_minor": amount_minor},
            {"account_code": "in_transit", "credit_minor": amount_minor},
        ],
    }


@pytest.fixture
def orphan_receipt(bank, internal_token, payment_payload):
    def _create() -> dict:
        payload = payment_payload()
        client_key = str(uuid4())
        status, receipt = bank.post_ledger_transaction(
            receipt_entries(payload["amount_minor"]),
            f"receipt:{payload['company_key']}:{client_key}",
            internal_token,
        )
        assert status == 201, f"não deu para lançar o recebimento órfão no Banco: {status} {receipt}"
        return {"payload": payload, "idempotency_key": client_key, "transaction_key": receipt["transaction_key"]}

    return _create
