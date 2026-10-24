from uuid import uuid4

from tests.integration.payout.conftest import payout_ledger_payload

RESPONSE_FIELDS = {
    "payout_key",
    "company_key",
    "account_key",
    "purpose",
    "destination",
    "status",
    "amount_minor",
    "fee_bps",
    "fee_minor",
    "failure_reason",
    "transaction_key",
    "attempts",
    "last_attempt_at",
}


class TestPayoutCreate:
    def test_creates_a_pending_payout(self, payouts, payout_payload):
        payload = payout_payload(amount_minor=12345)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 201
        assert set(response) == RESPONSE_FIELDS
        assert response["status"] == "pending"
        assert response["amount_minor"] == 12345
        assert response["account_key"] == payload["account_key"]
        assert response["purpose"] == payload["purpose"]
        assert response["destination"] == payload["destination"]
        assert response["failure_reason"] is None
        assert response["attempts"] == 0
        assert response["last_attempt_at"] is None
        assert len(response["payout_key"]) == 36
        assert len(response["company_key"]) == 36
        assert len(response["transaction_key"]) == 36

    def test_accepts_every_purpose(self, payouts, payout_payload):
        for purpose in ("withdrawal", "bill_payment", "transfer"):
            status, response = payouts.post_payout(payout_payload(purpose=purpose), str(uuid4()))
            assert status == 201
            assert response["purpose"] == purpose

    def test_destination_is_stored_as_sent(self, payouts, payout_payload):
        destination = {"barcode": "34191.79001 01043.510047 91020.150008 1 84770026000", "nested": {"a": [1, 2, {"b": None}]}}

        status, response = payouts.post_payout(payout_payload(destination=destination), str(uuid4()))

        assert status == 201
        assert response["destination"] == destination

    def test_accepts_scenario_inside_destination(self, payouts, payout_payload):
        destination = {"bank_code": "341", "scenario": "refuse"}

        status, response = payouts.post_payout(payout_payload(destination=destination), str(uuid4()))

        assert status == 201
        assert response["destination"] == destination

    def test_debit_exists_in_the_bank_under_the_derived_key(self, payouts, payout_payload, bank, internal_token):
        key = str(uuid4())

        status, payout = payouts.post_payout(payout_payload(amount_minor=777), key)
        assert status == 201

        ledger_key = f"payout:{payout['company_key']}:{key}"
        status, transaction = bank.post_ledger_transaction(payout_ledger_payload(payout), ledger_key, internal_token)
        assert status == 200
        assert transaction["transaction_key"] == payout["transaction_key"]
        assert transaction["type"] == "payout"
        assert transaction["status"] == "pending"

    def test_debit_leaves_the_account_without_the_funds(self, payouts, payout_payload):
        payload = payout_payload(funding_minor=1000, amount_minor=995)
        status, _ = payouts.post_payout(payload, str(uuid4()))
        assert status == 201

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 422
        assert response["code"] == "RNV001006"
