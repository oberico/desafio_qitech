from datetime import date, timedelta
from uuid import UUID

import pytest

from tests.utils.payload_generator import PayloadGenerator


ERROR_FIELDS = {"title", "description", "translation", "code"}


def birthdate_for_age(age_in_years: int, days_offset: int = 0) -> str:
    today = date.today()
    try:
        birthday = today.replace(year=today.year - age_in_years)
    except ValueError:
        birthday = date(today.year - age_in_years, 2, 28)
    return (birthday + timedelta(days=days_offset)).isoformat()


class TestClientCreate:
    def test_refuses_empty_body(self, clients):
        status, response = clients.post_client({})
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_body_that_is_not_an_object(self, clients):
        status, response = clients.post_client([])
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_unknown_field(self, clients):
        payload = PayloadGenerator.create_client_payload(unexpected=1)
        status, response = clients.post_client(payload)
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("field", ["cpf", "name", "birthdate", "email"])
    def test_refuses_missing_field(self, clients, field):
        payload = PayloadGenerator.create_client_payload()
        del payload[field]
        status, response = clients.post_client(payload)
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize(
        "field, value",
        [
            ("cpf", 52998224725),
            ("cpf", "52998224725"),
            ("name", None),
            ("name", ""),
            ("name", "a" * 256),
            ("birthdate", "17/05/1990"),
            ("email", "fulana"),
            ("email", "fulana@teste"),
            ("email", "a" * 250 + "@teste.com"),
        ],
    )
    def test_refuses_malformed_field(self, clients, field, value):
        payload = PayloadGenerator.create_client_payload(**{field: value})
        status, response = clients.post_client(payload)
        assert status == 400, f"o campo '{field}' aceitou o valor {value!r}"
        assert response["code"] == "RNV000001"

    def test_schema_error_description_names_the_offending_field(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate="17/05/1990")
        status, response = clients.post_client(payload)
        assert status == 400
        assert "birthdate" in response["description"]

    def test_error_response_has_the_standard_fields(self, clients):
        status, response = clients.post_client({})
        assert status == 400
        assert set(response) == ERROR_FIELDS

    def test_creates_client(self, clients):
        payload = PayloadGenerator.create_client_payload()
        status, response = clients.post_client(payload)
        assert status == 201
        UUID(response["client_key"])
        assert response["token"]

    def test_response_does_not_expose_internal_fields(self, clients):
        status, response = clients.post_client(PayloadGenerator.create_client_payload())
        assert status == 201
        assert "id" not in response
        assert "token_hash" not in response

    def test_two_clients_get_different_keys_and_tokens(self, clients):
        _, first = clients.post_client(PayloadGenerator.create_client_payload())
        _, second = clients.post_client(PayloadGenerator.create_client_payload())
        assert first["client_key"] != second["client_key"]
        assert first["token"] != second["token"]

    @pytest.mark.parametrize("cpf", ["111.222.333-44", "111.111.111-11"])
    def test_refuses_cpf_with_invalid_digits(self, clients, cpf):
        payload = PayloadGenerator.create_client_payload(cpf=cpf)
        status, response = clients.post_client(payload)
        assert status == 422
        assert response["code"] == "RNV001002"

    def test_refuses_duplicated_cpf(self, clients):
        first = PayloadGenerator.create_client_payload()
        status, _ = clients.post_client(first)
        assert status == 201

        second = PayloadGenerator.create_client_payload(cpf=first["cpf"])
        status, response = clients.post_client(second)
        assert status == 409
        assert response["code"] == "RNV001001"

    def test_refuses_duplicated_email(self, clients):
        first = PayloadGenerator.create_client_payload()
        status, _ = clients.post_client(first)
        assert status == 201

        second = PayloadGenerator.create_client_payload(email=first["email"])
        status, response = clients.post_client(second)
        assert status == 409
        assert response["code"] == "RNV001028"

    def test_refuses_underage(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(17))
        status, response = clients.post_client(payload)
        assert status == 422
        assert response["code"] == "RNV001029"

    def test_accepts_who_turns_eighteen_today(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(18))
        status, _ = clients.post_client(payload)
        assert status == 201

    def test_refuses_who_turns_eighteen_tomorrow(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(18, days_offset=1))
        status, response = clients.post_client(payload)
        assert status == 422
        assert response["code"] == "RNV001029"

    def test_refuses_birthdate_in_the_future(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(0, days_offset=1))
        status, response = clients.post_client(payload)
        assert status == 422
        assert response["code"] == "RNV001029"

    @pytest.mark.parametrize("birthdate", ["2000-02-30", "9999-99-99"])
    def test_refuses_impossible_birthdate(self, clients, birthdate):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate)
        status, response = clients.post_client(payload)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refused_request_does_not_take_the_cpf(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(17))
        status, _ = clients.post_client(payload)
        assert status == 422

        payload["birthdate"] = "1990-05-17"
        status, _ = clients.post_client(payload)
        assert status == 201
