import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


@pytest.fixture
def created_company(companies, client_token) -> tuple:
    payload = PayloadGenerator.create_company_payload()
    status, response = companies.post_company(payload, client_token)
    assert status == 201, f"não deu para criar a empresa do cenário: {status} {response}"
    return payload, response["company_key"]


class TestCompanyGet:
    def test_refuses_missing_token(self, companies, created_company):
        _, company_key = created_company
        status, response = companies.get_company(company_key)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_refuses_invalid_token(self, companies, created_company):
        _, company_key = created_company
        status, response = companies.get_company(company_key, "token-que-nao-existe")
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_returns_own_company(self, companies, client_token, created_company):
        payload, company_key = created_company
        status, response = companies.get_company(company_key, client_token)
        assert status == 200
        assert response["company_key"] == company_key
        assert response["cnpj"] == payload["cnpj"]
        assert response["legal_name"] == payload["legal_name"]

    def test_company_without_account_has_null_account_fields(self, companies, client_token, created_company):
        _, company_key = created_company
        status, response = companies.get_company(company_key, client_token)
        assert status == 200
        assert response["account_key"] is None
        assert response["account_status"] is None
        assert "has_account" not in response

    def test_response_does_not_expose_internal_fields(self, companies, client_token, created_company):
        _, company_key = created_company
        status, response = companies.get_company(company_key, client_token)
        assert status == 200
        assert "id" not in response
        assert "client_id" not in response

    def test_company_of_another_client_looks_nonexistent(self, companies, other_client_token, created_company):
        _, company_key = created_company
        status, response = companies.get_company(company_key, other_client_token)
        assert status == 404
        assert response["code"] == "RNV001018"

    def test_refuses_nonexistent_company(self, companies, client_token):
        status, response = companies.get_company(RandomGenerator.uuid(), client_token)
        assert status == 404
        assert response["code"] == "RNV001018"

    def test_refuses_malformed_company_key(self, companies, client_token):
        status, response = companies.get_company("x" * 36, client_token)
        assert status == 404
        assert response["code"] == "RNV001018"
