import pytest

from tests.integration.reconcile.conftest import BACKOFF_BASE_SECONDS, at, now, settlement_replay

pytestmark = pytest.mark.slow


@pytest.fixture(scope="class")
def timeline(new_payout, reconcile, payouts):
    payout = new_payout("flaky")
    t0 = now()
    steps = []
    for offset in (0, BACKOFF_BASE_SECONDS, BACKOFF_BASE_SECONDS * 3):
        _, response = reconcile.run(at(t0, offset))
        steps.append((response, payouts.get_payout(payout["payout_key"])[1]))
    return payout, steps


class TestPayoutReconcileFlaky:
    def test_first_two_attempts_leave_it_pending(self, timeline):
        payout, steps = timeline
        for attempts, (response, current) in enumerate(steps[:2], start=1):
            assert payout["payout_key"] in response["pending"]
            assert current["status"] == "pending"
            assert current["attempts"] == attempts

    def test_third_attempt_settles_it(self, timeline):
        payout, steps = timeline
        response, current = steps[2]
        assert payout["payout_key"] in response["settled"]
        assert current["status"] == "settled"
        assert current["attempts"] == 3
        assert current["failure_reason"] is None

    def test_settlement_entry_exists_in_the_bank(self, timeline, bank, internal_token):
        payout, _ = timeline
        status, replay = settlement_replay(bank, internal_token, payout)
        assert status == 200
        assert replay["type"] == "settlement"
