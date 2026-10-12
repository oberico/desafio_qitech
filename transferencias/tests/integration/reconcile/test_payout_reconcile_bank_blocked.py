from tests.integration.reconcile.conftest import at, now, reversal_replay


class TestPayoutReconcileBlockedAccount:
    def test_reversal_refused_by_the_bank_keeps_the_payout_pending(self, reconcile, bank, internal_token, payouts, new_payout):
        payout = new_payout("refuse")
        bank.block_account(payout["account_key"], internal_token)
        try:
            status, response = reconcile.run(at(now(), 0))
        finally:
            bank.unblock_account(payout["account_key"], internal_token)

        assert status == 200
        assert payout["payout_key"] in response["pending"]
        assert payout["payout_key"] not in response["failed"]
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "pending"
        assert current["failure_reason"] is None
        assert current["attempts"] == 1

    def test_next_run_after_unblock_completes_without_calling_the_mock_again(self, reconcile, bank, internal_token, payouts, new_payout):
        payout = new_payout("refuse")
        as_of = at(now(), 0)
        bank.block_account(payout["account_key"], internal_token)
        reconcile.run(as_of)
        bank.unblock_account(payout["account_key"], internal_token)

        status, response = reconcile.run(as_of)

        assert status == 200
        assert payout["payout_key"] in response["failed"]
        _, current = payouts.get_payout(payout["payout_key"])
        assert current["status"] == "failed"
        assert current["failure_reason"] == "interbank_refused"
        assert current["attempts"] == 1
        replay_status, _ = reversal_replay(bank, internal_token, payout)
        assert replay_status == 200
