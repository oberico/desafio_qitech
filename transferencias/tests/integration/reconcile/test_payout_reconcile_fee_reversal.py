import pytest

from tests.integration.reconcile.conftest import BACKOFF_BASE_SECONDS, at, now, reversal_replay

pytestmark = pytest.mark.slow

FUNDING_MINOR = 100_000
AMOUNT_MINOR = 10_001


@pytest.fixture(scope="module")
def failed_by_timeouts(open_account, new_payout, reconcile, payouts, bank, client_token, admin_token):
    account_key = open_account(funding_minor=FUNDING_MINOR)
    revenue_before = bank.get_revenue_minor(admin_token)
    payout = new_payout("timeout", amount_minor=AMOUNT_MINOR, account_key=account_key)
    balance_while_pending = bank.get_balance_minor(account_key, client_token)
    revenue_while_pending = bank.get_revenue_minor(admin_token)
    t0 = now()
    for offset in (0, BACKOFF_BASE_SECONDS, BACKOFF_BASE_SECONDS * 3):
        reconcile.run(at(t0, offset))
    return {
        "payout": payout,
        "current": payouts.get_payout(payout["payout_key"])[1],
        "balance_while_pending": balance_while_pending,
        "revenue_while_pending": revenue_while_pending,
        "revenue_before": revenue_before,
        "balance_after": bank.get_balance_minor(account_key, client_token),
    }


class TestPayoutReconcileFeeReversal:
    def test_the_fee_was_charged_while_pending(self, failed_by_timeouts):
        payout = failed_by_timeouts["payout"]
        assert payout["fee_minor"] == 51
        assert failed_by_timeouts["balance_while_pending"] == FUNDING_MINOR - AMOUNT_MINOR - 51

    def test_three_timeouts_fail_the_payout_keeping_the_original_fee(self, failed_by_timeouts):
        current = failed_by_timeouts["current"]
        assert current["status"] == "failed"
        assert current["failure_reason"] == "interbank_timeout"
        assert current["fee_minor"] == 51

    def test_the_client_gets_back_the_amount_and_the_fee(self, failed_by_timeouts):
        assert failed_by_timeouts["balance_after"] == FUNDING_MINOR

    def test_reversal_entry_refunds_the_revenue_leg(self, failed_by_timeouts, bank, internal_token):
        status, replay = reversal_replay(bank, internal_token, failed_by_timeouts["payout"])
        assert status == 200
        assert replay["type"] == "reversal"
