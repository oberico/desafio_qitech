from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator


class TestAccountCloseWithValuesInFlight:
    def test_refuses_closing_with_a_held_payment(self, bank, client_token, held_payment_account):
        account_key, _ = held_payment_account()

        status, response = bank.post_close(account_key, client_token)
        assert status == 422
        assert response["code"] == "RNV001035"

    def test_account_stays_active_after_refused_close(self, bank, client_token, held_payment_account):
        account_key, _ = held_payment_account()
        bank.post_close(account_key, client_token)

        status, response = bank.api.get(f"/accounts/{account_key}", {"Authorization": f"Bearer {client_token}"})
        assert status == 200
        assert response["status"] == "active"

    def test_closes_after_the_held_payment_is_refunded(self, bank, client_token, payments, held_payment_account):
        account_key, payment_key = held_payment_account()
        status, _ = payments.refund_payment(payment_key)
        assert status == 200

        status, response = bank.post_close(account_key, client_token)
        assert status == 200
        assert response["status"] == "closed"

    def test_refuses_closing_with_a_pending_payout_even_with_zero_balance(
        self, bank, client_token, payouts, funded_account
    ):
        account_key = funded_account(1005)
        payload = PayloadGenerator.create_payout_payload(account_key=account_key, amount_minor=1000)
        status, _ = payouts.post_payout(payload, str(uuid4()))
        assert status == 201

        status, response = bank.post_close(account_key, client_token)
        assert status == 422
        assert response["code"] == "RNV001035"

    def test_closes_a_clean_account(self, bank, client_token, funded_account):
        account_key = funded_account(0)

        status, response = bank.post_close(account_key, client_token)
        assert status == 200
        assert response["status"] == "closed"
