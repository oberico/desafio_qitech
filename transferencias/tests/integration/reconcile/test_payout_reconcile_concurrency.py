from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.integration.reconcile.conftest import at, now, settlement_replay

CONCURRENT_RUNS = 4


def run_concurrently(reconcile, as_of: str, runs: int = CONCURRENT_RUNS) -> list:
    with ThreadPoolExecutor(max_workers=runs) as pool:
        futures = [pool.submit(reconcile.run, as_of) for _ in range(runs)]
        return [future.result() for future in futures]


class TestPayoutReconcileConcurrency:
    def test_simultaneous_runs_settle_a_payout_once(self, reconcile, payouts, bank, internal_token, new_payout):
        payout = new_payout()

        results = run_concurrently(reconcile, at(now(), 0))

        assert all(status == 200 for status, _ in results)
        reporting = [response for _, response in results if payout["payout_key"] in response["settled"]]
        assert len(reporting) == 1
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "settled"
        assert current["attempts"] == 1
        replay_status, _ = settlement_replay(bank, internal_token, payout)
        assert replay_status == 200

    @pytest.mark.slow
    def test_simultaneous_runs_make_a_single_attempt(self, reconcile, payouts, new_payout):
        payout = new_payout("timeout")

        results = run_concurrently(reconcile, at(now(), 0), runs=2)

        assert all(status == 200 for status, _ in results)
        reporting = [response for _, response in results if payout["payout_key"] in response["pending"]]
        assert len(reporting) == 1
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "pending"
        assert current["attempts"] == 1
