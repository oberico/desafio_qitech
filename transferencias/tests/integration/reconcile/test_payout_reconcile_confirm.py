from datetime import datetime

import pytest

from tests.integration.reconcile.conftest import at, listed_in, now, settlement_replay


@pytest.mark.parametrize("scenario", [None, "confirm"], ids=["no_scenario", "confirm"])
class TestPayoutReconcileConfirm:
    def test_confirmed_payout_is_listed_as_settled(self, reconcile, new_payout, scenario):
        payout = new_payout(scenario)

        status, response = reconcile.run(at(now(), 0))

        assert status == 200
        assert payout["payout_key"] in response["settled"]
        assert payout["payout_key"] not in response["failed"]
        assert payout["payout_key"] not in response["pending"]

    def test_payout_becomes_settled_with_one_attempt_at_as_of(self, reconcile, payouts, new_payout, scenario):
        payout = new_payout(scenario)
        as_of = at(now(), 0)

        reconcile.run(as_of)

        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "settled"
        assert current["failure_reason"] is None
        assert current["attempts"] == 1
        assert datetime.fromisoformat(current["last_attempt_at"]) == datetime.fromisoformat(as_of)

    def test_settlement_entry_exists_in_the_bank(self, reconcile, bank, internal_token, new_payout, scenario):
        payout = new_payout(scenario)
        reconcile.run(at(now(), 0))

        status, replay = settlement_replay(bank, internal_token, payout)

        assert status == 200
        assert replay["type"] == "settlement"
        assert replay["status"] == "settled"

    def test_running_again_does_not_touch_a_settled_payout(self, reconcile, payouts, new_payout, scenario):
        payout = new_payout(scenario)
        as_of = at(now(), 0)
        reconcile.run(as_of)

        status, response = reconcile.run(as_of)

        assert status == 200
        assert payout["payout_key"] not in listed_in(response)
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "settled"
        assert current["attempts"] == 1
