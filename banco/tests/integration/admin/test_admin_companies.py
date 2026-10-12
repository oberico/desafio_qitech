import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

ROUTE = "/admin/companies"
PAGE_FIELDS = {"data", "limit", "cursor", "is_last_page"}
COMPANY_FIELDS = {"company_key", "cnpj", "legal_name", "account_key", "account_status"}


class TestAdminCompanies:
    def test_returns_a_page(self, admin, admin_token, create_company, client_token):
        create_company(client_token)
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert set(response) == PAGE_FIELDS

    def test_newest_company_comes_first_with_company_fields(self, admin, admin_token, companies, client_token):
        status, created = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
        assert status == 201

        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        first = response["data"][0]
        assert set(first) == COMPANY_FIELDS
        assert first == created

    def test_company_without_account_has_null_account(self, admin, admin_token, create_company, client_token):
        company_key = create_company(client_token)
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert response["data"][0]["company_key"] == company_key
        assert response["data"][0]["account_key"] is None
        assert response["data"][0]["account_status"] is None

    def test_company_shows_its_account(self, admin, admin_token, accounts, create_company, client_token):
        company_key = create_company(client_token)
        status, account = accounts.post_account(company_key, client_token)
        assert status == 201

        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert response["data"][0]["account_key"] == account["account_key"]
        assert response["data"][0]["account_status"] == "active"

    def test_lists_companies_of_every_client(
        self, admin, admin_token, create_company, client_token, other_client_token
    ):
        first = create_company(client_token)
        second = create_company(other_client_token)

        status, response = admin.get(ROUTE, admin_token, {"limit": 2})
        assert status == 200
        assert [company["company_key"] for company in response["data"]] == [second, first]

    def test_cursor_walks_the_pages_without_repeating_or_skipping(
        self, admin, admin_token, create_company, client_token
    ):
        created_keys = [create_company(client_token) for _ in range(3)]

        seen = []
        params = {"limit": 1}
        for _ in range(3):
            status, response = admin.get(ROUTE, admin_token, params)
            assert status == 200
            assert response["is_last_page"] is False
            seen.extend(company["company_key"] for company in response["data"])
            params = {"limit": 1, "cursor": response["cursor"]}

        assert seen == list(reversed(created_keys))

    @pytest.mark.parametrize(
        "params, code",
        [
            ({"limit": "0"}, "RNV000009"),
            ({"limit": "101"}, "RNV000009"),
            ({"cursor": RandomGenerator.uuid()}, "RNV000011"),
            ({"cursor": "x"}, "RNV000011"),
            ({"cursor": ""}, "RNV000011"),
            ({"pagina": "2"}, "RNV000008"),
        ],
        ids=["limit_zero", "limit_too_big", "public_key_cursor", "malformed_cursor", "empty_cursor", "unknown_parameter"],
    )
    def test_refuses_invalid_query(self, admin, admin_token, params, code):
        status, response = admin.get(ROUTE, admin_token, params)
        assert status == 400
        assert response["code"] == code
