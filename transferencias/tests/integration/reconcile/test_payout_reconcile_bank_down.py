import os

import pytest

from tests.integration.reconcile.conftest import at, now, reversal_replay
from tests.utils.reconcile_requests import ReconcileRequests
from tests.utils.request_generator import RequestGenerator

TRANSFERENCIAS_FAULT_API_URL = os.getenv("TRANSFERENCIAS_FAULT_API_URL", "http://localhost:8012")

pytestmark = pytest.mark.fault


@pytest.fixture(scope="module")
def fault_reconcile(internal_token) -> ReconcileRequests:
    try:
        RequestGenerator(TRANSFERENCIAS_FAULT_API_URL).get("/health_check")
    except Exception:
        pytest.exit(
            f"could not reach the fault API at {TRANSFERENCIAS_FAULT_API_URL}; run `docker compose --profile fault up -d` first",
            returncode=1,
        )
    return ReconcileRequests(TRANSFERENCIAS_FAULT_API_URL, internal_token)


class TestPayoutReconcileBankDown:
    def test_ledger_down_keeps_a_confirmed_payout_pending(self, fault_reconcile, payouts, new_payout):
        payout = new_payout()

        status, response = fault_reconcile.run(at(now(), 0))

        assert status == 200
        assert payout["payout_key"] in response["pending"]
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "pending"
        assert current["attempts"] == 1

    def test_next_healthy_run_settles_it_without_a_new_attempt(self, fault_reconcile, reconcile, payouts, new_payout):
        payout = new_payout()
        as_of = at(now(), 0)
        fault_reconcile.run(as_of)

        _, response = reconcile.run(as_of)

        assert payout["payout_key"] in response["settled"]
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["attempts"] == 1

    def test_ledger_down_keeps_a_refused_payout_pending_and_the_next_run_reverses_it(
        self, fault_reconcile, reconcile, bank, internal_token, payouts, new_payout
    ):
        payout = new_payout("refuse")
        as_of = at(now(), 0)

        _, response = fault_reconcile.run(as_of)
        _, pending = payouts.get_payout(payout["payout_key"])
        _, healthy = reconcile.run(as_of)
        _, failed = payouts.get_payout(payout["payout_key"])

        assert payout["payout_key"] in response["pending"]
        assert pending["status"] == "pending"
        assert payout["payout_key"] in healthy["failed"]
        assert failed["status"] == "failed"
        assert failed["attempts"] == 1
        assert reversal_replay(bank, internal_token, payout)[0] == 200
