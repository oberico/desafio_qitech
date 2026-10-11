from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4


def receipt_payload(amount_minor: int) -> dict:
    return {
        "type": "receipt",
        "entries": [
            {"account_code": "reserves", "debit_minor": amount_minor},
            {"account_code": "in_transit", "credit_minor": amount_minor},
        ],
    }


class TestPaymentLedger:
    def test_payment_carries_the_receipt_transaction_key(self, payments, payment_payload):
        status, response = payments.post_payment(payment_payload(), str(uuid4()))

        assert status == 201
        assert len(response["transaction_key"]) == 36

    def test_receipt_exists_in_the_bank_under_the_derived_key(self, payments, payment_payload, bank, internal_token):
        key = str(uuid4())
        payload = payment_payload(amount_minor=12345)

        status, payment = payments.post_payment(payload, key)
        assert status == 201

        ledger_key = f"receipt:{payload['company_key'].lower()}:{key}"
        status, transaction = bank.post_ledger_transaction(receipt_payload(12345), ledger_key, internal_token)
        assert status == 200
        assert transaction["transaction_key"] == payment["transaction_key"]

    def test_sequential_retry_keeps_the_same_transaction_key(self, payments, payment_payload):
        key = str(uuid4())
        payload = payment_payload()

        _, first = payments.post_payment(payload, key)
        status, second = payments.post_payment(payload, key)

        assert status == 200
        assert second["transaction_key"] == first["transaction_key"]

    def test_concurrent_requests_create_one_payment_and_one_receipt(self, payments, payment_payload):
        key = str(uuid4())
        payload = payment_payload()

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: payments.post_payment(payload, key), range(10)))

        assert sorted(status for status, _ in results) == [200] * 9 + [201]
        assert len({response["payment_key"] for _, response in results}) == 1
        assert len({response["transaction_key"] for _, response in results}) == 1
        assert results[0][1]["transaction_key"] is not None
