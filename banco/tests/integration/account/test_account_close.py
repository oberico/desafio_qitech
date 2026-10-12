import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestAccountClose:
    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_token(self, accounts, active_account, token):
        status, response = accounts.close(active_account, token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_closes_account_with_zero_balance(self, accounts, active_account, client_token):
        status, response = accounts.close(active_account, client_token)
        assert status == 200
        assert response["account_key"] == active_account
        assert response["status"] == "closed"

    def test_closed_status_is_persisted(self, accounts, active_account, client_token):
        status, _ = accounts.close(active_account, client_token)
        assert status == 200

        status, response = accounts.get_account(active_account, client_token)
        assert status == 200
        assert response["status"] == "closed"

    def test_company_shows_its_closed_account(self, accounts, companies, create_company, client_token):
        company_key = create_company(client_token)
        status, created = accounts.post_account(company_key, client_token)
        assert status == 201
        status, _ = accounts.close(created["account_key"], client_token)
        assert status == 200

        status, response = companies.get_company(company_key, client_token)
        assert status == 200
        assert response["account_status"] == "closed"

    def test_refuses_closing_an_already_closed_account(self, accounts, active_account, client_token):
        status, _ = accounts.close(active_account, client_token)
        assert status == 200

        status, response = accounts.close(active_account, client_token)
        assert status == 409
        assert response["code"] == "RNV001009"

    def test_refuses_closing_a_rejected_account(self, accounts, open_account, client_token):
        account_key = open_account(client_token, RandomGenerator.cnpj_rejected_by_bureau())

        status, response = accounts.close(account_key, client_token)
        assert status == 409
        assert response["code"] == "RNV001009"

        status, response = accounts.get_account(account_key, client_token)
        assert status == 200
        assert response["status"] == "rejected"

    def test_refuses_closing_an_account_with_balance(self, accounts, active_account, client_token, credit_account):
        credit_account(active_account, 10000)

        status, response = accounts.close(active_account, client_token)

        assert status == 409
        assert response["code"] == "RNV001012"

        status, response = accounts.get_account(active_account, client_token)
        assert response["status"] == "active"

    def test_closes_account_after_withdrawing_everything(
        self, accounts, ledger, active_account, client_token, credit_account
    ):
        credit_account(active_account, 10000)
        payout = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ],
        )
        status, _ = ledger.post_transaction(payout, RandomGenerator.uuid())
        assert status == 201

        status, response = accounts.close(active_account, client_token)

        assert status == 200
        assert response["status"] == "closed"

    def test_account_of_another_client_looks_nonexistent(self, accounts, active_account, other_client_token):
        status, response = accounts.close(active_account, other_client_token)
        assert status == 404
        assert response["code"] == "RNV001021"

    def test_refused_close_by_another_client_keeps_account_active(
        self, accounts, active_account, client_token, other_client_token
    ):
        status, _ = accounts.close(active_account, other_client_token)
        assert status == 404

        status, response = accounts.get_account(active_account, client_token)
        assert status == 200
        assert response["status"] == "active"

    @pytest.mark.parametrize("account_key", [RandomGenerator.uuid(), "x" * 36], ids=["nonexistent", "malformed"])
    def test_refuses_unknown_account(self, accounts, client_token, account_key):
        status, response = accounts.close(account_key, client_token)
        assert status == 404
        assert response["code"] == "RNV001021"
