import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestAuthMe:
    @pytest.mark.parametrize(
        "internal_token", [None, "internal-token-errado"], ids=["missing_internal_token", "wrong_internal_token"]
    )
    def test_refuses_missing_or_wrong_internal_token(self, clients, client_token, internal_token):
        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refuses_client_token_used_as_internal_token(self, clients, client_token):
        status, response = clients.get_auth_me(client_token, client_token)
        assert status == 403
        assert response["code"] == "RNV000002"

    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_client_token(self, clients, internal_token, token):
        status, response = clients.get_auth_me(token, internal_token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_internal_token_is_checked_before_client_token(self, clients):
        status, response = clients.get_auth_me("token-que-nao-existe", "internal-token-errado")
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_returns_identity_of_the_token_owner(self, clients, internal_token, created_client):
        _, created = created_client
        status, response = clients.get_auth_me(created["token"], internal_token)
        assert status == 200
        assert response["client_key"] == created["client_key"]

    def test_response_does_not_expose_internal_fields(self, clients, internal_token, client_token):
        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        for internal_field in ("id", "token", "token_hash"):
            assert internal_field not in response

    def test_client_without_companies_has_empty_list(self, clients, internal_token, client_token):
        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert response["companies"] == []

    def test_company_without_account_has_null_account(self, clients, companies, internal_token, client_token):
        status, company = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
        assert status == 201

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert response["companies"] == [
            {"company_key": company["company_key"], "account_key": None, "account_status": None}
        ]

    def test_lists_every_company_of_the_client(self, clients, companies, internal_token, client_token):
        created_keys = set()
        for _ in range(2):
            status, company = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
            assert status == 201
            created_keys.add(company["company_key"])

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert {company["company_key"] for company in response["companies"]} == created_keys

    def test_does_not_list_companies_of_other_clients(
        self, clients, companies, internal_token, client_token, other_client_token
    ):
        status, _ = companies.post_company(PayloadGenerator.create_company_payload(), other_client_token)
        assert status == 201

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert response["companies"] == []

    def test_company_with_active_account(self, clients, accounts, internal_token, client_token, create_company):
        company_key = create_company(client_token)
        status, account = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert response["companies"] == [
            {"company_key": company_key, "account_key": account["account_key"], "account_status": "active"}
        ]

    def test_company_with_rejected_account(self, clients, accounts, internal_token, client_token, create_company):
        company_key = create_company(client_token, RandomGenerator.cnpj_rejected_by_bureau())
        status, account = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert response["companies"] == [
            {"company_key": company_key, "account_key": account["account_key"], "account_status": "rejected"}
        ]

    def test_company_with_closed_account(self, clients, accounts, internal_token, client_token, create_company):
        company_key = create_company(client_token)
        status, account = accounts.post_account(company_key, client_token)
        assert status == 201
        status, _ = accounts.close(account["account_key"], client_token)
        assert status == 200

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        assert response["companies"][0]["account_status"] == "closed"

    def test_lists_companies_with_and_without_account(
        self, clients, accounts, internal_token, client_token, create_company
    ):
        with_account = create_company(client_token)
        status, account = accounts.post_account(with_account, client_token)
        assert status == 201
        without_account = create_company(client_token)

        status, response = clients.get_auth_me(client_token, internal_token)
        assert status == 200
        companies = {company["company_key"]: company for company in response["companies"]}
        assert companies.keys() == {with_account, without_account}
        assert companies[with_account]["account_key"] == account["account_key"]
        assert companies[without_account]["account_key"] is None
