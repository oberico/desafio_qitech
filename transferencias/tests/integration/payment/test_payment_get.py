from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPaymentGet:
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
        assert set(response) == ERROR_FIELDS

    def test_payment_of_another_client_is_not_found(self, payments, other_payments):
        payload = PayloadGenerator.create_payment_payload()
        _, created = payments.post_payment(payload, str(uuid4()))

        status, response = other_payments.get_payment(created["payment_key"])

        assert status == 404
        assert response["code"] == "RNV001025"
