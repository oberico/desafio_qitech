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


class TestRefundBankLedgerDown:
    def test_ledger_down_returns_service_unavailable_and_the_payment_stays_held(
        self, fault_payments, payments, payment_payload
    ):
        _, payment = payments.post_payment(payment_payload(), str(uuid4()))

        status, response = fault_payments.refund_payment(payment["payment_key"])

        assert status == 503
        assert response["code"] == "RNV001017"
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "held"

    def test_the_refund_works_afterwards_through_the_healthy_api(self, fault_payments, payments, payment_payload):
        _, payment = payments.post_payment(payment_payload(), str(uuid4()))
        fault_payments.refund_payment(payment["payment_key"])

        status, response = payments.refund_payment(payment["payment_key"])

        assert status == 200
        assert response["status"] == "refunded"
