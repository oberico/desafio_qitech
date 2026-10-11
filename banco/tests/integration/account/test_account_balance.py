from concurrent.futures import ThreadPoolExecutor

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

INTERNAL_FIELDS = ("id", "account_id", "company_id", "class_id", "status_id", "code", "normal_balance")

class TestAccountBalance:
    def test_new_account_has_zero_balance(self, accounts, active_account, client_token):
        status, response = accounts.get_balance(active_account, client_token)

        assert status == 200
        assert response["account_key"] == active_account
        assert response["balance_minor"] == 0
        assert response["currency"] == "brl"

    def test_balance_shows_credited_amount(self, accounts, active_account, client_token, credit_account):
        credit_account(active_account, 10000)

        status, response = accounts.get_balance(active_account, client_token)

        assert status == 200
        assert response["balance_minor"] == 10000

    def test_balance_subtracts_payouts(self, accounts, ledger, active_account, client_token, credit_account):
        credit_account(active_account, 10000)
        payout = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 3000},
                {"account_code": "in_transit", "credit_minor": 3000},
            ],
        )
        status, _ = ledger.post_transaction(payout, RandomGenerator.uuid())
        assert status == 201

        status, response = accounts.get_balance(active_account, client_token)

        assert status == 200
        assert response["balance_minor"] == 7000

    def test_concurrent_credits_all_add_up(self, accounts, active_account, client_token, credit_account):
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda _: credit_account(active_account, 1000), range(10)))

        status, response = accounts.get_balance(active_account, client_token)

        assert status == 200
        assert response["balance_minor"] == 10000

    def test_response_does_not_expose_internal_fields(self, accounts, active_account, client_token):
        status, response = accounts.get_balance(active_account, client_token)

        assert status == 200
        for internal_field in INTERNAL_FIELDS:
            assert internal_field not in response
