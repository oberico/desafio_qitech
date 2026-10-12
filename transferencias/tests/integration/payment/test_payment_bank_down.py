import os
from uuid import uuid4

import pytest

from tests.utils.payment_requests import PaymentRequests
from tests.utils.request_generator import RequestGenerator

TRANSFERENCIAS_FAULT_API_URL = os.getenv("TRANSFERENCIAS_FAULT_API_URL", "http://localhost:8012")

pytestmark = pytest.mark.fault


@pytest.fixture(scope="module")
def fault_payments(bank, client_token) -> PaymentRequests:
    fault_api = RequestGenerator(TRANSFERENCIAS_FAULT_API_URL)
    try:
        fault_api.get("/health_check")
    except Exception:
        pytest.exit(
            f"could not reach the fault API at {TRANSFERENCIAS_FAULT_API_URL}; run `docker compose --profile fault up -d` first",
            returncode=1,
        )
    return PaymentRequests(fault_api, client_token)


class TestPaymentBankLedgerDown:
    def test_ledger_down_returns_service_unavailable(self, fault_payments, payment_payload):
        status, response = fault_payments.post_payment(payment_payload(), str(uuid4()))
        assert status == 503
        assert response["code"] == "RNV001017"

    def test_nothing_is_saved_and_the_key_is_released(self, fault_payments, payments, payment_payload):
        key = str(uuid4())
        payload = payment_payload()

        status, response = fault_payments.post_payment(payload, key)
        assert status == 503
        assert response["code"] == "RNV001017"

        status, _ = payments.post_payment(payload, key)
        assert status == 201
