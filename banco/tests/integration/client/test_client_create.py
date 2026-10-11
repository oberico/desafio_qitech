from concurrent.futures import ThreadPoolExecutor
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
    @pytest.mark.parametrize(
        "body",
        [{}, [], PayloadGenerator.create_client_payload(unexpected=1)],
        ids=["empty_body", "not_an_object", "unknown_field"],
    )
    def test_refuses_invalid_body(self, clients, body):
        status, response = clients.post_client(body)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_invalid_body_description_names_the_body_readably(self, clients):
        _, response = clients.post_client([])
        assert response["description"].startswith("The request does not match the expected schema: body: ")
        assert "('" not in response["description"]

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
        ids=[
            "cpf_as_number",
            "cpf_without_punctuation",
            "name_null",
            "name_empty",
            "name_256_characters",
            "birthdate_in_brazilian_format",
            "email_without_at",
            "email_without_domain_dot",
            "email_over_255_characters",
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

    @pytest.mark.parametrize("cpf", ["111.222.333-44", "111.111.111-11"], ids=["wrong_check_digits", "repeated_digits"])
    def test_refuses_cpf_with_invalid_digits(self, clients, cpf):
        payload = PayloadGenerator.create_client_payload(cpf=cpf)
        status, response = clients.post_client(payload)
        assert status == 422
        assert response["code"] == "RNV001002"

    @pytest.mark.parametrize(
        "field, code",
        [("cpf", "RNV001001"), ("email", "RNV001028")],
        ids=["duplicated_cpf", "duplicated_email"],
    )
    def test_refuses_duplicated_identity(self, clients, field, code):
        first = PayloadGenerator.create_client_payload()
        status, _ = clients.post_client(first)
        assert status == 201

        second = PayloadGenerator.create_client_payload(**{field: first[field]})
        status, response = clients.post_client(second)
        assert status == 409
        assert response["code"] == code

    def test_accepts_who_turns_eighteen_today(self, clients):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(18))
        status, _ = clients.post_client(payload)
        assert status == 201

    @pytest.mark.parametrize(
        "birthdate",
        [birthdate_for_age(17), birthdate_for_age(18, days_offset=1)],
        ids=["seventeen_years_old", "turns_eighteen_tomorrow"],
    )
    def test_refuses_underage(self, clients, birthdate):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate)
        status, response = clients.post_client(payload)
        assert status == 422
        assert response["code"] == "RNV001029"

    @pytest.mark.parametrize(
        "birthdate",
        ["2000-02-30", "9999-99-99", birthdate_for_age(0, days_offset=1)],
        ids=["nonexistent_day", "nonexistent_month", "tomorrow"],
    )
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

    def test_concurrent_registrations_with_same_cpf_create_a_single_client(self, clients):
        payload = PayloadGenerator.create_client_payload()

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: clients.post_client(payload), range(10)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [201] + [409] * 9
        assert {response["code"] for status, response in results if status == 409} <= {"RNV001001", "RNV001028"}
