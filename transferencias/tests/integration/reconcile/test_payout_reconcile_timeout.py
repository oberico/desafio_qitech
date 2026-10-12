from datetime import datetime

import pytest

from tests.integration.reconcile.conftest import BACKOFF_BASE_SECONDS, at, listed_in, now, reversal_replay

pytestmark = pytest.mark.slow

FIRST_WAIT = BACKOFF_BASE_SECONDS
SECOND_WAIT = BACKOFF_BASE_SECONDS * 2


@pytest.fixture(scope="module")
def timeline(new_payout, reconcile, payouts):
    payout = new_payout("timeout")
    key = payout["payout_key"]
    t0 = now()
    steps = {}

    def run(name: str, offset: int) -> None:
        _, response = reconcile.run(at(t0, offset))
        _, current = payouts.get_payout(key)
        steps[name] = (response, current)

    run("first_attempt", 0)
    run("before_first_wait", FIRST_WAIT - 1)
    run("second_attempt", FIRST_WAIT)
    run("before_second_wait", FIRST_WAIT + SECOND_WAIT - 1)
    run("third_attempt", FIRST_WAIT + SECOND_WAIT)
    run("after_failed", FIRST_WAIT + SECOND_WAIT + 10 * SECOND_WAIT)
    return payout, t0, steps


class TestPayoutReconcileTimeout:
    def test_first_timeout_leaves_the_payout_pending_and_listed(self, timeline):
        payout, _, steps = timeline
        response, current = steps["first_attempt"]
        assert payout["payout_key"] in response["pending"]
        assert current["status"] == "pending"
        assert current["attempts"] == 1

    def test_attempt_is_recorded_at_as_of(self, timeline):
        _, t0, steps = timeline
        _, current = steps["first_attempt"]
        assert datetime.fromisoformat(current["last_attempt_at"]) == datetime.fromisoformat(at(t0, 0))

    def test_run_before_the_first_wait_makes_no_attempt(self, timeline):
        payout, _, steps = timeline
        response, current = steps["before_first_wait"]
        assert payout["payout_key"] not in listed_in(response)
        assert current["status"] == "pending"
        assert current["attempts"] == 1

    def test_second_attempt_happens_once_the_first_wait_elapsed(self, timeline):
        payout, t0, steps = timeline
        response, current = steps["second_attempt"]
        assert payout["payout_key"] in response["pending"]
        assert current["attempts"] == 2
        assert datetime.fromisoformat(current["last_attempt_at"]) == datetime.fromisoformat(at(t0, FIRST_WAIT))

    def test_second_wait_is_double_the_first(self, timeline):
        payout, _, steps = timeline
        response, current = steps["before_second_wait"]
        assert payout["payout_key"] not in listed_in(response)
        assert current["status"] == "pending"
        assert current["attempts"] == 2


class TestPayoutReconcileTimeoutExhaustion:
    def test_third_timeout_fails_the_payout(self, timeline):
        payout, _, steps = timeline
        response, current = steps["third_attempt"]
        assert payout["payout_key"] in response["failed"]
        assert current["status"] == "failed"
        assert current["failure_reason"] == "interbank_timeout"
        assert current["attempts"] == 3

    def test_reversal_entry_exists_in_the_bank(self, timeline, bank, internal_token):
        payout, _, _ = timeline
        status, replay = reversal_replay(bank, internal_token, payout)
        assert status == 200
        assert replay["type"] == "reversal"

    def test_a_failed_payout_is_never_attempted_again(self, timeline):
        payout, _, steps = timeline
        response, current = steps["after_failed"]
        assert payout["payout_key"] not in listed_in(response)
        assert current["status"] == "failed"
        assert current["attempts"] == 3


class TestPayoutReconcileTimeoutExhaustionWithBlockedAccount:
    @pytest.fixture(scope="class")
    def timeline(self, new_payout, reconcile, payouts, bank, internal_token):
        payout = new_payout("timeout")
        t0 = now()
        steps = {}
        for offset in (0, FIRST_WAIT):
            reconcile.run(at(t0, offset))
        bank.block_account(payout["account_key"], internal_token)
        try:
            _, response = reconcile.run(at(t0, FIRST_WAIT + SECOND_WAIT))
            steps["blocked"] = (response, payouts.get_payout(payout["payout_key"])[1])
        finally:
            bank.unblock_account(payout["account_key"], internal_token)
        _, response = reconcile.run(at(t0, FIRST_WAIT + SECOND_WAIT))
        steps["unblocked"] = (response, payouts.get_payout(payout["payout_key"])[1])
        return payout, steps

    def test_blocked_account_keeps_the_exhausted_payout_pending(self, timeline):
        payout, steps = timeline
        response, current = steps["blocked"]
        assert payout["payout_key"] in response["pending"]
        assert current["status"] == "pending"
        assert current["attempts"] == 3

    def test_next_run_after_unblock_fails_it_without_a_fourth_attempt(self, timeline, bank, internal_token):
        payout, steps = timeline
        response, current = steps["unblocked"]
        assert payout["payout_key"] in response["failed"]
        assert current["status"] == "failed"
        assert current["attempts"] == 3
        status, _ = reversal_replay(bank, internal_token, payout)
        assert status == 200
