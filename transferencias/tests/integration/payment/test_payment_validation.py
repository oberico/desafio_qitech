from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


def payload_without_method() -> dict:
    payload = PayloadGenerator.create_payment_payload()
    del payload["method"]
    return payload


INVALID_BODIES = {
    "empty_body": (lambda: {}, "RNV000007"),
    "missing_method": (payload_without_method, "RNV000007"),
    "unknown_method": (lambda: PayloadGenerator.create_payment_payload(method="invalid"), "RNV000009"),
    "unknown_field": (lambda: PayloadGenerator.create_payment_payload(unexpected=1), "RNV000008"),
    "amount_as_string": (lambda: PayloadGenerator.create_payment_payload(amount_minor="1000"), "RNV000009"),
    "fractional_amount": (lambda: PayloadGenerator.create_payment_payload(amount_minor=110.5), "RNV000009"),
    "float_typed_whole_amount": (lambda: PayloadGenerator.create_payment_payload(amount_minor=110.0), "RNV000009"),
    "malformed_company_key": (lambda: PayloadGenerator.create_payment_payload(company_key="x" * 36), "RNV000009"),
    "account_key_in_body": (lambda: PayloadGenerator.create_payment_payload(account_key=RandomGenerator.uuid()), "RNV000008"),
}


class TestPaymentValidation:
    @pytest.mark.parametrize("build_payload, code", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_refuses_invalid_body(self, payments, build_payload, code):
        status, response = payments.post_payment(build_payload(), str(uuid4()))
        assert status == 400
        assert response["code"] == code

    def test_refuses_missing_idempotency_key(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        status, response = payments.post_payment(payload, None)
        assert status == 400
        assert response["code"] == "RNV000012"

    def test_missing_idempotency_key_description_is_readable(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        _, response = payments.post_payment(payload, None)
        assert response["description"].startswith("The request does not match the expected schema: header.")
        assert "('" not in response["description"]

    def test_schema_error_description_names_the_offending_field(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="carrier_pigeon")
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert "method" in response["description"]

    def test_schema_error_has_exactly_the_four_documented_fields_filled(self, payments):
        status, response = payments.post_payment({}, str(uuid4()))
        assert status == 400
        assert set(response) == ERROR_FIELDS
        assert all(response[field] for field in ERROR_FIELDS)

    def test_refuses_invalid_amount(self, payments, payment_payload):
        payload = payment_payload(amount_minor=0)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"
        assert response["translation"] == "O valor precisa ser maior que zero."
        assert set(response) == ERROR_FIELDS
        assert all(response[field] for field in ERROR_FIELDS)
