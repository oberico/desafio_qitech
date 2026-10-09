from uuid import uuid4

from testkit.transferencias import PayloadGenerator


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

    def test_refuses_invalid_amount(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=0)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001020"

    def test_creates_payment_in_pending(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 201

        payment_key = response["payment_key"]

        status, response = payments.get_payment(payment_key)
        assert status == 200
        assert response["payment_key"] == payment_key
        assert response["status"] == "pending"
        assert response["amount_minor"] == payload["amount_minor"]
        assert response["origin"] == payload["origin"]
        assert response["transaction_key"] is None
