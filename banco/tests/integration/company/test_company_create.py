from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest

from tests.utils.payload_generator import PayloadGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestCompanyCreate:
    @pytest.mark.parametrize(
        "body",
        [{}, PayloadGenerator.create_company_payload(unexpected=1)],
        ids=["empty_body", "unknown_field"],
    )
    def test_refuses_invalid_body(self, companies, client_token, body):
        status, response = companies.post_company(body, client_token)
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("field", ["cnpj", "legal_name"])
    def test_refuses_missing_field(self, companies, client_token, field):
        payload = PayloadGenerator.create_company_payload()
        del payload[field]
        status, response = companies.post_company(payload, client_token)
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize(
        "field, value",
        [
            ("cnpj", 11222333000181),
            ("cnpj", "11222333000181"),
            ("cnpj", "529.982.247-25"),
            ("legal_name", None),
            ("legal_name", ""),
            ("legal_name", "   "),
            ("legal_name", "a" * 256),
        ],
        ids=[
            "cnpj_as_number",
            "cnpj_without_punctuation",
            "cnpj_in_cpf_format",
            "legal_name_null",
            "legal_name_empty",
            "legal_name_only_spaces",
            "legal_name_256_characters",
        ],
    )
    def test_refuses_malformed_field(self, companies, client_token, field, value):
        payload = PayloadGenerator.create_company_payload(**{field: value})
        status, response = companies.post_company(payload, client_token)
        assert status == 400, f"o campo '{field}' aceitou o valor {value!r}"
        assert response["code"] == "RNV000001"

    def test_schema_error_description_names_the_offending_field(self, companies, client_token):
        payload = PayloadGenerator.create_company_payload(cnpj="11222333000181")
        status, response = companies.post_company(payload, client_token)
        assert status == 400
        assert "cnpj" in response["description"]

    def test_error_response_has_the_standard_fields(self, companies, client_token):
        status, response = companies.post_company({}, client_token)
        assert status == 400
        assert set(response) == ERROR_FIELDS

    def test_creates_company(self, companies, client_token):
        payload = PayloadGenerator.create_company_payload()
        status, response = companies.post_company(payload, client_token)
        assert status == 201
        UUID(response["company_key"])
        assert response["cnpj"] == payload["cnpj"]
        assert response["legal_name"] == payload["legal_name"]
        assert response["account_key"] is None
        assert response["account_status"] is None

    def test_response_does_not_expose_internal_fields(self, companies, client_token):
        status, response = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
        assert status == 201
        assert "id" not in response
        assert "client_id" not in response

    def test_created_company_belongs_to_the_token_owner(self, companies, client_token):
        status, created = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
        assert status == 201

        status, response = companies.get_company(created["company_key"], client_token)
        assert status == 200
        assert response["company_key"] == created["company_key"]

    def test_client_can_own_more_than_one_company(self, companies, client_token):
        status, first = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
        assert status == 201

        status, second = companies.post_company(PayloadGenerator.create_company_payload(), client_token)
        assert status == 201
        assert first["company_key"] != second["company_key"]

    @pytest.mark.parametrize("cnpj", ["11.222.333/0001-82", "00.000.000/0000-00"], ids=["wrong_check_digits", "repeated_digits"])
    def test_refuses_cnpj_with_invalid_digits(self, companies, client_token, cnpj):
        payload = PayloadGenerator.create_company_payload(cnpj=cnpj)
        status, response = companies.post_company(payload, client_token)
        assert status == 422
        assert response["code"] == "RNV001020"

    @pytest.mark.parametrize("second_owner", ["client_token", "other_client_token"], ids=["same_client", "another_client"])
    def test_refuses_duplicated_cnpj(self, request, companies, client_token, second_owner):
        first = PayloadGenerator.create_company_payload()
        status, _ = companies.post_company(first, client_token)
        assert status == 201

        second = PayloadGenerator.create_company_payload(cnpj=first["cnpj"])
        status, response = companies.post_company(second, request.getfixturevalue(second_owner))
        assert status == 409
        assert response["code"] == "RNV001019"

    def test_refused_request_does_not_take_the_cnpj(self, companies, client_token):
        payload = PayloadGenerator.create_company_payload(legal_name="")
        status, _ = companies.post_company(payload, client_token)
        assert status == 400

        payload["legal_name"] = "Loja da Fulana LTDA"
        status, _ = companies.post_company(payload, client_token)
        assert status == 201

    def test_concurrent_registrations_with_same_cnpj_create_a_single_company(self, companies, client_token):
        payload = PayloadGenerator.create_company_payload()

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: companies.post_company(payload, client_token), range(10)))

        assert sorted(status for status, _ in results) == [201] + [409] * 9
        assert {response["code"] for status, response in results if status == 409} == {"RNV001019"}
