import pytest

from tests.utils.random_generator import RandomGenerator

INTERNAL_FIELDS = ("id", "company_id", "class_id", "status_id", "code", "normal_balance")


class TestAccountGet:
    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_token(self, accounts, active_account, token):
        status, response = accounts.get_account(active_account, token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_returns_own_account(self, accounts, create_company, client_token):
        company_key = create_company(client_token)
        status, created = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = accounts.get_account(created["account_key"], client_token)
        assert status == 200
        assert response["account_key"] == created["account_key"]
        assert response["company_key"] == company_key
        assert response["status"] == "active"

    def test_returns_the_contract_fields(self, accounts, active_account, client_token):
        status, response = accounts.get_account(active_account, client_token)
        assert status == 200
        assert set(response) == {"account_key", "company_key", "status", "currency", "created_at"}
        assert response["currency"] == "brl"
        assert response["created_at"]

    def test_returns_rejected_account(self, accounts, open_account, client_token):
        account_key = open_account(client_token, RandomGenerator.cnpj_rejected_by_bureau())
        status, response = accounts.get_account(account_key, client_token)
        assert status == 200
        assert response["status"] == "rejected"

    def test_response_does_not_expose_internal_fields(self, accounts, active_account, client_token):
        status, response = accounts.get_account(active_account, client_token)
        assert status == 200
        for internal_field in INTERNAL_FIELDS:
            assert internal_field not in response

    def test_account_of_another_client_looks_nonexistent(self, accounts, active_account, other_client_token):
        status, response = accounts.get_account(active_account, other_client_token)
        assert status == 404
        assert response["code"] == "RNV001021"

    @pytest.mark.parametrize("account_key", [RandomGenerator.uuid(), "x" * 36], ids=["nonexistent", "malformed"])
    def test_refuses_unknown_account(self, accounts, client_token, account_key):
        status, response = accounts.get_account(account_key, client_token)
        assert status == 404
        assert response["code"] == "RNV001021"
