import os

import pytest

from tests.integration.settlement.conftest import due_instant
from tests.utils.payment_requests import PaymentRequests
from tests.utils.request_generator import RequestGenerator
from tests.utils.settlement_requests import SettlementRequests

TRANSFERENCIAS_FAULT_API_URL = os.getenv("TRANSFERENCIAS_FAULT_API_URL", "http://localhost:8012")

pytestmark = pytest.mark.fault


@pytest.fixture(scope="module")
def fault_settlements(internal_token) -> SettlementRequests:
    try:
        RequestGenerator(TRANSFERENCIAS_FAULT_API_URL).get("/health_check")
    except Exception:
        pytest.exit(
            f"could not reach the fault API at {TRANSFERENCIAS_FAULT_API_URL}; run `docker compose --profile fault up -d` first",
            returncode=1,
        )
    return SettlementRequests(TRANSFERENCIAS_FAULT_API_URL, internal_token)


class TestSettlementBankLedgerDown:
    def test_ledger_down_defers_and_the_payment_stays_held(self, fault_settlements, payments, held_payment):
        payment = held_payment()

        status, response = fault_settlements.run(due_instant(payment))

        assert status == 200
        assert payment["payment_key"] in response["deferred"]
        assert payment["payment_key"] not in response["settled"]
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "held"

    def test_the_next_healthy_run_releases_it(self, fault_settlements, settlements, payments, held_payment):
        payment = held_payment()
        as_of = due_instant(payment)
        fault_settlements.run(as_of)

        _, response = settlements.run(as_of)

        assert payment["payment_key"] in response["settled"]
