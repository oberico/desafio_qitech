from uuid import uuid4


class TestPaymentIdempotency:
    def test_replay_returns_original_with_200(self, payments, payment_payload):
        key = str(uuid4())
        payload = payment_payload()

        status, first = payments.post_payment(payload, key)
        assert status == 201

        status, second = payments.post_payment(payload, key)
        assert status == 200
        assert second["payment_key"] == first["payment_key"]

    def test_same_content_in_other_order_is_replay(self, payments, payment_payload):
        key = str(uuid4())
        payload = payment_payload()
        reordered = dict(reversed(list(payload.items())))

        status, first = payments.post_payment(payload, key)
        assert status == 201

        status, second = payments.post_payment(reordered, key)
        assert status == 200
        assert second["payment_key"] == first["payment_key"]

    def test_reused_key_with_other_content_is_refused(self, payments, payment_payload):
        key = str(uuid4())
        payload = payment_payload()

        status, _ = payments.post_payment(payload, key)
        assert status == 201

        payload["amount_minor"] = payload["amount_minor"] + 1
        status, response = payments.post_payment(payload, key)
        assert status == 422
        assert response["code"] == "RNV001024"

    def test_same_key_in_other_company_is_a_new_payment(self, payments, payment_payload):
        key = str(uuid4())

        status, first = payments.post_payment(payment_payload(), key)
        assert status == 201

        status, second = payments.post_payment(payment_payload(), key)
        assert status == 201
        assert second["payment_key"] != first["payment_key"]

    def test_concurrent_replays_create_a_single_payment(self, payments, payment_payload):
        from concurrent.futures import ThreadPoolExecutor

        key = str(uuid4())
        payload = payment_payload()

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: payments.post_payment(payload, key), range(10)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [200] * 9 + [201]
        assert len({response["payment_key"] for _, response in results}) == 1
