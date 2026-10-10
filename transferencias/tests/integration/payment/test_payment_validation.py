from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator


ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPaymentValidation:
    def test_refuses_empty_body(self, payments):
        status, response = payments.post_payment({}, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_missing_idempotency_key(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        status, response = payments.post_payment(payload, None)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_missing_method(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        del payload["method"]
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_unknown_method(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="invalid")
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_unknown_field(self, payments):
        payload = PayloadGenerator.create_payment_payload(unexpected=1)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_amount_as_string(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor="1000")
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_fractional_amount(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=110.5)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_float_typed_amount_even_when_whole(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=110.0)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_malformed_company_key(self, payments):
        payload = PayloadGenerator.create_payment_payload(company_key="x" * 36)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_schema_error_description_names_the_offending_field(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="carrier_pigeon")
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 400
        assert "method" in response["description"]

    def test_schema_error_has_exactly_the_four_documented_fields(self, payments):
        status, response = payments.post_payment({}, str(uuid4()))
        assert status == 400
        assert set(response) == ERROR_FIELDS

    def test_business_error_has_exactly_the_four_documented_fields(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=0)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 422
        assert set(response) == ERROR_FIELDS

    def test_error_texts_are_filled(self, payments):
        status, response = payments.post_payment({}, str(uuid4()))
        assert status == 400
        assert response["title"] and response["description"] and response["translation"]

    def test_refuses_invalid_amount(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=0)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"
