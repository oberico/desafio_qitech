from uuid import uuid4

from tests.integration.payout.conftest import payout_ledger_payload

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPayoutInsufficientFunds:
    def test_bank_refusal_is_forwarded_to_the_client(self, payouts, payout_payload):
        payload = payout_payload(funding_minor=1000, amount_minor=1001)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 422
        assert response["code"] == "RNV001006"
        assert set(response) == ERROR_FIELDS

    def test_account_without_any_funds_is_refused(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(funding_minor=0), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001006"

    def test_nothing_is_saved_and_the_key_is_released(self, payouts, payout_payload, bank, internal_token):
        key = str(uuid4())
        payload = payout_payload(funding_minor=1000, amount_minor=1001)

        status, response = payouts.post_payout(payload, key)
        assert status == 422
        assert response["code"] == "RNV001006"

        funding = {
            "type": "receipt",
            "entries": [
                {"account_code": "reserves", "debit_minor": 5000},
                {"account_key": payload["account_key"], "credit_minor": 5000},
            ],
        }
        status, _ = bank.post_ledger_transaction(funding, str(uuid4()), internal_token)
        assert status == 201

        status, payout = payouts.post_payout(payload, key)
        assert status == 201
        assert payout["status"] == "pending"

    def test_balance_exactly_equal_to_the_amount_is_enough(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(funding_minor=1000, amount_minor=1000), str(uuid4()))
        assert status == 201
        assert response["amount_minor"] == 1000
