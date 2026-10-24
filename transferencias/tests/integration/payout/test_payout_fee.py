from uuid import uuid4

from tests.integration.payout.conftest import payout_ledger_payload
from tests.utils.payout_fee import SEEDED_FEE_BPS, payout_fee_minor

FUNDING_MINOR = 1_000_000


class TestPayoutFeeCharge:
    def test_response_carries_the_snapshot_of_the_fee(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(amount_minor=10_000), str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == SEEDED_FEE_BPS
        assert response["fee_minor"] == 50

    def test_fee_rounds_up_to_the_next_cent(self, payouts, payout_payload):
        amount_minor = 10_001

        status, response = payouts.post_payout(payout_payload(amount_minor=amount_minor), str(uuid4()))

        assert status == 201
        assert payout_fee_minor(amount_minor) == 51
        assert response["fee_minor"] == 51
        assert isinstance(response["fee_minor"], int)

    def test_client_is_debited_the_amount_plus_the_fee(self, payouts, payout_payload, bank, client_token):
        payload = payout_payload(funding_minor=FUNDING_MINOR, amount_minor=10_001)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 201
        balance = bank.get_balance_minor(payload["account_key"], client_token)
        assert balance == FUNDING_MINOR - 10_001 - response["fee_minor"]

    def test_revenue_receives_the_fee(self, payouts, payout_payload, bank, admin_token):
        payload = payout_payload(amount_minor=10_001)
        revenue_before = bank.get_revenue_minor(admin_token)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 201
        assert bank.get_revenue_minor(admin_token) - revenue_before == response["fee_minor"] == 51

    def test_ledger_entry_has_the_revenue_leg(self, payouts, payout_payload, bank, internal_token):
        key = str(uuid4())
        status, payout = payouts.post_payout(payout_payload(amount_minor=10_001), key)
        assert status == 201

        ledger_key = f"payout:{payout['company_key']}:{key}"
        status, transaction = bank.post_ledger_transaction(payout_ledger_payload(payout), ledger_key, internal_token)

        assert status == 200
        assert transaction["transaction_key"] == payout["transaction_key"]

    def test_zero_fee_omits_the_revenue_leg(self, payouts, payout_payload, changed_payout_fee, bank, admin_token):
        changed_payout_fee(0)
        payload = payout_payload(funding_minor=1000, amount_minor=1000)
        revenue_before = bank.get_revenue_minor(admin_token)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == 0
        assert response["fee_minor"] == 0
        assert bank.get_revenue_minor(admin_token) == revenue_before


class TestPayoutFeeInsufficientFunds:
    def test_balance_covers_the_amount_but_not_the_fee(self, payouts, payout_payload):
        payload = payout_payload(funding_minor=10_000, amount_minor=10_000)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 422
        assert response["code"] == "RNV001006"

    def test_refused_payout_leaves_the_balance_and_the_revenue_untouched(
        self, payouts, payout_payload, bank, client_token, admin_token
    ):
        payload = payout_payload(funding_minor=10_000, amount_minor=10_000)
        revenue_before = bank.get_revenue_minor(admin_token)

        payouts.post_payout(payload, str(uuid4()))

        assert bank.get_balance_minor(payload["account_key"], client_token) == 10_000
        assert bank.get_revenue_minor(admin_token) == revenue_before


class TestPayoutFeeSnapshot:
    def test_changing_the_fee_does_not_change_a_payout_already_created(
        self, payouts, payout_payload, changed_payout_fee
    ):
        status, created = payouts.post_payout(payout_payload(amount_minor=10_000), str(uuid4()))
        assert status == 201

        changed_payout_fee(1000)

        status, current = payouts.get_payout(created["payout_key"])
        assert status == 200
        assert current["fee_bps"] == SEEDED_FEE_BPS
        assert current["fee_minor"] == created["fee_minor"] == 50

    def test_new_payouts_use_the_new_version(self, payouts, payout_payload, changed_payout_fee):
        changed_payout_fee(1000)

        status, response = payouts.post_payout(payout_payload(amount_minor=10_000), str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == 1000
        assert response["fee_minor"] == 1000

    def test_retry_after_the_fee_changed_returns_the_original_fee(self, payouts, payout_payload, changed_payout_fee):
        key = str(uuid4())
        payload = payout_payload(amount_minor=10_000)
        _, first = payouts.post_payout(payload, key)

        changed_payout_fee(1000)
        status, retry = payouts.post_payout(payload, key)

        assert status == 200
        assert retry["fee_bps"] == SEEDED_FEE_BPS
        assert retry["fee_minor"] == first["fee_minor"]


class TestPayoutFeeIdempotency:
    def test_retry_returns_the_same_payout_and_charges_the_fee_once(
        self, payouts, payout_payload, bank, client_token, admin_token
    ):
        key = str(uuid4())
        payload = payout_payload(funding_minor=FUNDING_MINOR, amount_minor=10_000)
        revenue_before = bank.get_revenue_minor(admin_token)

        status, first = payouts.post_payout(payload, key)
        assert status == 201
        status, second = payouts.post_payout(payload, key)

        assert status == 200
        assert second == first
        assert bank.get_balance_minor(payload["account_key"], client_token) == FUNDING_MINOR - 10_000 - 50
        assert bank.get_revenue_minor(admin_token) - revenue_before == 50

    def test_same_key_with_another_payload_is_refused(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload(amount_minor=10_000)
        payouts.post_payout(payload, key)

        status, response = payouts.post_payout({**payload, "amount_minor": 10_001}, key)

        assert status == 422
        assert response["code"] == "RNV001024"
