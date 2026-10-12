import os

import pytest

from tests.integration.receipt_reconcile.conftest import after_the_grace
from tests.utils.receipt_reconcile_requests import ReceiptReconcileRequests
from tests.utils.request_generator import RequestGenerator

TRANSFERENCIAS_FAULT_API_URL = os.getenv("TRANSFERENCIAS_FAULT_API_URL", "http://localhost:8012")

pytestmark = pytest.mark.fault


@pytest.fixture(scope="module")
def fault_receipt_reconcile(internal_token) -> ReceiptReconcileRequests:
    try:
        RequestGenerator(TRANSFERENCIAS_FAULT_API_URL).get("/health_check")
    except Exception:
        pytest.exit(
            f"could not reach the fault API at {TRANSFERENCIAS_FAULT_API_URL}; run `docker compose --profile fault up -d` first",
            returncode=1,
        )
    return ReceiptReconcileRequests(TRANSFERENCIAS_FAULT_API_URL, internal_token)


class TestReceiptReconcileLedgerDown:
    def test_ledger_down_defers_the_refund(self, fault_receipt_reconcile, orphan_receipt):
        orphan = orphan_receipt()

        status, response = fault_receipt_reconcile.run(after_the_grace())

        assert status == 200
        assert orphan["transaction_key"] in response["deferred"]
        assert orphan["transaction_key"] not in response["refunded"]

    def test_the_next_healthy_run_refunds_it(self, fault_receipt_reconcile, receipt_reconcile, orphan_receipt):
        orphan = orphan_receipt()
        fault_receipt_reconcile.run(after_the_grace())

        status, response = receipt_reconcile.run(after_the_grace())

        assert status == 200
        assert orphan["transaction_key"] in response["refunded"]
