from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest

from tests.utils.random_generator import RandomGenerator

INTERNAL_FIELDS = ("id", "company_id", "class_id", "status_id", "code", "normal_balance")


class TestAccountOpen:
    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_token(self, accounts, create_company, client_token, token):
        company_key = create_company(client_token)
        status, response = accounts.post_account(company_key, token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_opens_active_account_when_bureau_approves(self, accounts, create_company, client_token):
        company_key = create_company(client_token)
        status, response = accounts.post_account(company_key, client_token)
        assert status == 201
        UUID(response["account_key"])
        assert response["company_key"] == company_key
        assert response["status"] == "active"

    def test_opens_rejected_account_when_bureau_rejects(self, accounts, create_company, client_token):
        company_key = create_company(client_token, RandomGenerator.cnpj_rejected_by_bureau())
        status, response = accounts.post_account(company_key, client_token)
        assert status == 201
        assert response["status"] == "rejected"

    def test_response_does_not_expose_internal_fields(self, accounts, create_company, client_token):
        company_key = create_company(client_token)
        status, response = accounts.post_account(company_key, client_token)
        assert status == 201
        for internal_field in INTERNAL_FIELDS:
            assert internal_field not in response

    def test_opened_account_can_be_read_by_its_owner(self, accounts, create_company, client_token):
        company_key = create_company(client_token)
        status, created = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = accounts.get_account(created["account_key"], client_token)
        assert status == 200
        assert response["account_key"] == created["account_key"]
        assert response["status"] == "active"

    def test_company_shows_its_opened_account(self, accounts, companies, create_company, client_token):
        company_key = create_company(client_token)
        status, created = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = companies.get_company(company_key, client_token)
        assert status == 200
        assert response["account_key"] == created["account_key"]
        assert response["account_status"] == "active"

    def test_company_shows_its_rejected_account(self, accounts, companies, create_company, client_token):
        company_key = create_company(client_token, RandomGenerator.cnpj_rejected_by_bureau())
        status, created = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = companies.get_company(company_key, client_token)
        assert status == 200
        assert response["account_key"] == created["account_key"]
        assert response["account_status"] == "rejected"

    def test_refuses_company_of_another_client(self, accounts, create_company, client_token, other_client_token):
        company_key = create_company(client_token)
        status, response = accounts.post_account(company_key, other_client_token)
        assert status == 404
        assert response["code"] == "RNV001018"

    @pytest.mark.parametrize("company_key", [RandomGenerator.uuid(), "x" * 36], ids=["nonexistent", "malformed"])
    def test_refuses_unknown_company(self, accounts, client_token, company_key):
        status, response = accounts.post_account(company_key, client_token)
        assert status == 404
        assert response["code"] == "RNV001018"

    def test_refuses_second_account_for_the_same_company(self, accounts, create_company, client_token):
        company_key = create_company(client_token)
        status, _ = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = accounts.post_account(company_key, client_token)
        assert status == 409
        assert response["code"] == "RNV001022"

    def test_refuses_new_account_after_bureau_rejection(self, accounts, create_company, client_token):
        company_key = create_company(client_token, RandomGenerator.cnpj_rejected_by_bureau())
        status, response = accounts.post_account(company_key, client_token)
        assert status == 201
        assert response["status"] == "rejected"

        status, response = accounts.post_account(company_key, client_token)
        assert status == 409
        assert response["code"] == "RNV001022"

    def test_concurrent_requests_open_a_single_account(self, accounts, create_company, client_token):
        company_key = create_company(client_token)

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: accounts.post_account(company_key, client_token), range(10)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [201] + [409] * 9
        assert all(response["code"] == "RNV001022" for status, response in results if status == 409)

    def test_each_company_of_the_same_client_gets_its_own_account(self, accounts, create_company, client_token):
        status, first = accounts.post_account(create_company(client_token), client_token)
        assert status == 201

        status, second = accounts.post_account(create_company(client_token), client_token)
        assert status == 201
        assert first["account_key"] != second["account_key"]
