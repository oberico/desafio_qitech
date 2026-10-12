from tests.integration.reconcile.conftest import MAX_PER_RUN, at, listed_in, now

EXTRA_PAYOUTS = 1
RUNS_TO_DRAIN = 10


class TestPayoutReconcileCap:
    def test_a_run_processes_at_most_the_cap_and_later_runs_finish_the_rest(self, reconcile, payouts, open_account, new_payout):
        account_key = open_account(funding_minor=(MAX_PER_RUN + EXTRA_PAYOUTS) * 1_000)
        mine = {new_payout(account_key=account_key)["payout_key"] for _ in range(MAX_PER_RUN + EXTRA_PAYOUTS)}
        as_of = at(now(), 0)

        status, first = reconcile.run(as_of)

        assert status == 200
        assert len(listed_in(first)) == MAX_PER_RUN

        for _ in range(RUNS_TO_DRAIN):
            _, response = reconcile.run(as_of)
            if not listed_in(response):
                break

        statuses = {payouts.get_payout(key)[1]["status"] for key in mine}
        assert statuses == {"settled"}
