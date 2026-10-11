from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestLedgerTransactionCreate:
    def test_refuses_missing_internal_token(self, api):
        status, response = api.post("/ledger/transactions", body={})
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refuses_empty_body(self, ledger):
        status, response = ledger.post_transaction({}, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_missing_idempotency_key(self, api, internal_token):
        payload = PayloadGenerator.create_ledger_transaction_payload()
        headers = {"INTERNAL-TOKEN": internal_token}
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_creates_transaction(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload()
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201
        assert response["transaction_key"]
        assert response["type"] == "receipt"
        assert response["status"] == "settled"
        assert response["created_at"]

    def test_refuses_unbalanced_entries(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 9000},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 422
        assert response["code"] == "RNV001015"

    def test_refuses_unknown_account(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_key": RandomGenerator.uuid(), "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 404
        assert response["code"] == "RNV001021"

    @pytest.mark.skip(reason="depends on the account routes")
    def test_refuses_inactive_account(self, ledger):
        ...

    @pytest.mark.skip(reason="depends on the account routes")
    def test_refuses_insufficient_funds(self, ledger):
        ...

    def test_refuses_unknown_referenced_transaction(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=RandomGenerator.uuid(),
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 404
        assert response["code"] == "RNV001016"

    def test_refuses_already_settled_transaction(self, ledger):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        receipt_key = receipt_response["transaction_key"]

        first_settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, _ = ledger.post_transaction(first_settlement, RandomGenerator.uuid())
        assert status == 201

        second_settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, response = ledger.post_transaction(second_settlement, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_replay_returns_200(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload()
        idempotency_key = RandomGenerator.uuid()
        _, first_response = ledger.post_transaction(payload, idempotency_key)

        status, response = ledger.post_transaction(payload, idempotency_key)
        assert status == 200
        assert response["transaction_key"] == first_response["transaction_key"]

    def test_refuses_reused_key_with_other_content(self, ledger):
        idempotency_key = RandomGenerator.uuid()
        payload = PayloadGenerator.create_ledger_transaction_payload()
        ledger.post_transaction(payload, idempotency_key)

        other_payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 5000},
                {"account_code": "in_transit", "credit_minor": 5000},
            ],
        )
        status, response = ledger.post_transaction(other_payload, idempotency_key)
        assert status == 422
        assert response["code"] == "RNV001024"

    def test_refuses_already_reversed_transaction(self, ledger):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        receipt_key = receipt_response["transaction_key"]

        refund_entries = [
            {"account_code": "in_transit", "debit_minor": 10000},
            {"account_code": "reserves", "credit_minor": 10000},
        ]
        first_refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=refund_entries,
        )
        status, _ = ledger.post_transaction(first_refund, RandomGenerator.uuid())
        assert status == 201

        second_refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=refund_entries,
        )
        status, response = ledger.post_transaction(second_refund, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_refuses_unknown_type(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(type="banana")
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_zero_amount(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 0},
                {"account_code": "in_transit", "credit_minor": 0},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_negative_amount(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": -10000},
                {"account_code": "in_transit", "credit_minor": -10000},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_entry_with_debit_and_credit(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 10000, "credit_minor": 10000},
                {"account_code": "in_transit", "debit_minor": 10000, "credit_minor": 10000},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_concurrent_replays_create_one_transaction(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload()
        idempotency_key = RandomGenerator.uuid()

        def send(_):
            return ledger.post_transaction(payload, idempotency_key)

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(send, range(10)))

        statuses = sorted(status for status, _ in results)
        keys = {response["transaction_key"] for _, response in results}
        assert statuses == [200] * 9 + [201]
        assert len(keys) == 1

    def test_refuses_settling_reversed_transaction(self, ledger):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        receipt_key = receipt_response["transaction_key"]

        refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        status, _ = ledger.post_transaction(refund, RandomGenerator.uuid())
        assert status == 201

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, response = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_refuses_reversing_settled_transaction(self, ledger):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        receipt_key = receipt_response["transaction_key"]

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 201

        refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        status, response = ledger.post_transaction(refund, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"