from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tests.utils.settlement_requests import SettlementRequests


@pytest.fixture(scope="session")
def settlements(api_url, internal_token) -> SettlementRequests:
    return SettlementRequests(api_url, internal_token)


@pytest.fixture
def held_payment(payments, payment_payload):
    def _create(**overrides) -> dict:
        status, payment = payments.post_payment(payment_payload(**overrides), str(uuid4()))
        assert status == 201, f"could not create the payment: {status} {payment}"
        return payment

    return _create


def due_instant(payment: dict) -> str:
    return (datetime.fromisoformat(payment["release_at"]) + timedelta(seconds=1)).isoformat()


def before_instant(payment: dict) -> str:
    return (datetime.fromisoformat(payment["release_at"]) - timedelta(seconds=1)).isoformat()


def settlement_ledger_payload(payment: dict, net_minor: int, fee_minor: int) -> dict:
    entries = []
    if net_minor > 0:
        entries.append({"account_code": "in_transit", "debit_minor": net_minor})
    if fee_minor > 0:
        entries.append({"account_code": "in_transit", "debit_minor": fee_minor})
    if net_minor > 0:
        entries.append({"account_key": payment["account_key"], "credit_minor": net_minor})
    if fee_minor > 0:
        entries.append({"account_code": "revenue", "credit_minor": fee_minor})
    return {"type": "settlement", "settles_transaction_key": payment["transaction_key"], "entries": entries}
