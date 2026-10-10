from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator


ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPaymentCreate:
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

    def test_creates_payment_held_with_snapshot(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=10000, method="pix")
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["status"] == "held"
        assert response["amount_minor"] == 10000
        assert response["method"] == "pix"
        assert response["fee_bps"] == 99
        assert response["transaction_key"] is None
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=23, minutes=59) <= release_at <= before + timedelta(hours=24, minutes=1)

    def test_boleto_snapshots_its_own_fee_and_window(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="boleto")
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == 199
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=71, minutes=59) <= release_at <= before + timedelta(hours=72, minutes=1)

    def test_card_snapshots_its_own_fee_and_window(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="card")
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == 499
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=719, minutes=59) <= release_at <= before + timedelta(hours=720, minutes=1)

    def test_amount_above_float_precision_is_stored_exactly(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=9_007_199_254_740_993)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 201
        assert response["amount_minor"] == 9_007_199_254_740_993
        assert isinstance(response["amount_minor"], int)

    def test_amount_is_returned_as_an_integer(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=11000)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 201
        assert isinstance(response["amount_minor"], int)

    def test_gets_created_payment_by_key(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        _, created = payments.post_payment(payload, str(uuid4()))

        status, response = payments.get_payment(created["payment_key"])

        assert status == 200
        assert response["payment_key"] == created["payment_key"]
        assert response["status"] == "held"

    def test_get_unknown_payment_is_not_found(self, payments):
        status, response = payments.get_payment(str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001025"

    def test_not_found_error_has_exactly_the_four_documented_fields(self, payments):
        status, response = payments.get_payment(str(uuid4()))
        assert status == 404
        assert set(response) == ERROR_FIELDS
