from datetime import datetime
from uuid import uuid4

from tests.integration.reconcile.conftest import at, listed_in, now, reversal_replay
from tests.utils.payload_generator import PayloadGenerator


class TestPayoutReconcileRefuse:
    def test_refused_payout_is_listed_as_failed(self, reconcile, new_payout):
        payout = new_payout("refuse")

        status, response = reconcile.run(at(now(), 0))

        assert status == 200
        assert payout["payout_key"] in response["failed"]
        assert payout["payout_key"] not in response["settled"]
        assert payout["payout_key"] not in response["pending"]

    def test_payout_fails_at_once_with_one_attempt_and_a_reason(self, reconcile, payouts, new_payout):
        payout = new_payout("refuse")
        as_of = at(now(), 0)

        reconcile.run(as_of)

        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "failed"
        assert current["failure_reason"] == "interbank_refused"
        assert current["attempts"] == 1
        assert datetime.fromisoformat(current["last_attempt_at"]) == datetime.fromisoformat(as_of)

    def test_reversal_entry_exists_in_the_bank(self, reconcile, bank, internal_token, new_payout):
        payout = new_payout("refuse")
        reconcile.run(at(now(), 0))

        status, replay = reversal_replay(bank, internal_token, payout)

        assert status == 200
        assert replay["type"] == "reversal"

    def test_the_money_returns_to_the_account(self, reconcile, payouts, open_account, new_payout):
        account_key = open_account(funding_minor=7_000)
        new_payout("refuse", amount_minor=6_965, account_key=account_key)
        reconcile.run(at(now(), 0))

        retry = PayloadGenerator.create_payout_payload(account_key=account_key, amount_minor=6_965)
        status, response = payouts.post_payout(retry, str(uuid4()))

        assert status == 201, f"the reversal did not give the money back: {response}"

    def test_running_again_neither_retries_nor_duplicates(self, reconcile, bank, internal_token, payouts, new_payout):
        payout = new_payout("refuse")
        as_of = at(now(), 0)
        reconcile.run(as_of)

        status, response = reconcile.run(as_of)

        assert status == 200
        assert payout["payout_key"] not in listed_in(response)
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "failed"
        assert current["attempts"] == 1
        replay_status, _ = reversal_replay(bank, internal_token, payout)
        assert replay_status == 200
