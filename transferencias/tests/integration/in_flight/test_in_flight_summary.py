from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestInFlightAccess:
    def test_refuses_missing_internal_token(self, in_flight):
        status, response = in_flight.get_in_flight(str(uuid4()), internal_token="")
        assert status == 403
        assert response["code"] == "RNV000002"
        assert set(response) == ERROR_FIELDS

    def test_refuses_wrong_internal_token(self, in_flight):
        status, response = in_flight.get_in_flight(str(uuid4()), internal_token="wrong-token")
        assert status == 403
        assert response["code"] == "RNV000002"


class TestInFlightSummary:
    def test_unknown_account_has_nothing_in_flight(self, in_flight):
        status, response = in_flight.get_in_flight(str(uuid4()))
        assert status == 200
        assert response == {"held_payments": 0, "pending_payouts": 0}

    def test_counts_a_held_payment(self, in_flight, held_payment_account):
        account_key, _ = held_payment_account()

        status, response = in_flight.get_in_flight(account_key)
        assert status == 200
        assert response == {"held_payments": 1, "pending_payouts": 0}

    def test_ignores_a_refunded_payment(self, in_flight, payments, held_payment_account):
        account_key, payment_key = held_payment_account()
        status, _ = payments.refund_payment(payment_key)
        assert status == 200

        status, response = in_flight.get_in_flight(account_key)
        assert status == 200
        assert response == {"held_payments": 0, "pending_payouts": 0}

    def test_counts_a_pending_payout(self, in_flight, payouts, funded_account):
        account_key = funded_account()
        status, _ = payouts.post_payout(PayloadGenerator.create_payout_payload(account_key=account_key, amount_minor=1000), str(uuid4()))
        assert status == 201

        status, response = in_flight.get_in_flight(account_key)
        assert status == 200
        assert response == {"held_payments": 0, "pending_payouts": 1}

    def test_does_not_count_items_of_another_account(self, in_flight, held_payment_account, funded_account):
        held_payment_account()

        status, response = in_flight.get_in_flight(funded_account())
        assert status == 200
        assert response == {"held_payments": 0, "pending_payouts": 0}
