from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


def payload_without_method() -> dict:
    payload = PayloadGenerator.create_payment_payload()
    del payload["method"]
    return payload


INVALID_BODIES = {
    "empty_body": lambda: {},
    "missing_method": payload_without_method,
    "unknown_method": lambda: PayloadGenerator.create_payment_payload(method="invalid"),
    "unknown_field": lambda: PayloadGenerator.create_payment_payload(unexpected=1),
    "amount_as_string": lambda: PayloadGenerator.create_payment_payload(amount_minor="1000"),
    "fractional_amount": lambda: PayloadGenerator.create_payment_payload(amount_minor=110.5),
    "float_typed_whole_amount": lambda: PayloadGenerator.create_payment_payload(amount_minor=110.0),
    "malformed_company_key": lambda: PayloadGenerator.create_payment_payload(company_key="x" * 36),
    "malformed_account_key": lambda: PayloadGenerator.create_payment_payload(account_key="x" * 36),
}


class TestPaymentValidation:
    @pytest.mark.parametrize("build_payload", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_refuses_invalid_body(self, payments, build_payload):
        status, response = payments.post_payment(build_payload(), str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_missing_idempotency_key(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        status, response = payments.post_payment(payload, None)
        assert status == 400
        assert response["code"] == "RNV000001"

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

    def test_refuses_invalid_amount(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=0)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"
        assert set(response) == ERROR_FIELDS
        assert all(response[field] for field in ERROR_FIELDS)
