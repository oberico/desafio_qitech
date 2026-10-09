from uuid import uuid4

from testkit.transferencias import PayloadGenerator


class TestPaymentIdempotency:
    def test_replay_returns_original_with_200(self, payments):
        key = str(uuid4())
        payload = PayloadGenerator.create_payment_payload()

        status, first = payments.post_payment(payload, key)
        assert status == 201

        status, second = payments.post_payment(payload, key)
        assert status == 200
        assert second["payment_key"] == first["payment_key"]

    def test_same_content_in_other_order_is_replay(self, payments):
        key = str(uuid4())
        payload = PayloadGenerator.create_payment_payload()
        reordered = dict(reversed(list(payload.items())))

        status, first = payments.post_payment(payload, key)
        assert status == 201

        status, second = payments.post_payment(reordered, key)
        assert status == 200
        assert second["payment_key"] == first["payment_key"]

    def test_reused_key_with_other_content_is_refused(self, payments):
        key = str(uuid4())
        payload = PayloadGenerator.create_payment_payload()

        status, _ = payments.post_payment(payload, key)
        assert status == 201

        payload["amount_minor"] = payload["amount_minor"] + 1
        status, response = payments.post_payment(payload, key)
        assert status == 422
        assert response["code"] == "RNV001024"

    def test_same_key_in_other_company_is_a_new_payment(self, payments):
        key = str(uuid4())

        status, first = payments.post_payment(PayloadGenerator.create_payment_payload(), key)
        assert status == 201

        status, second = payments.post_payment(PayloadGenerator.create_payment_payload(), key)
        assert status == 201
        assert second["payment_key"] != first["payment_key"]
