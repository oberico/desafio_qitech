import os 
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator
from concurrent.futures import ThreadPoolExecutor
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "internal-token-dev")

class TestLedgerTransactionCreate:
    def test_refuses_missing_internal_token(self, api):
        status, response = api.post("/ledger/transactions", body={})
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refuses_empty_body(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        status, response = api.post("/ledger/transactions", body={}, headers= headers)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_creates_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload()
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 201
        assert response["transaction_key"]
        assert response["type"] == "receipt"
        assert response["status"] == "settled"
        assert response["created_at"]


    def test_refuses_unbalanced_entries(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 9000},
            ]
        )
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 422
        assert response["code"] == "RNV001015"


    def test_refuses_unknown_account(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_key": RandomGenerator.uuid(), "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ]
        )
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 404
        assert response["code"] == "RNV001021" 

    # def test_refuses_inactive_account(self, api):
    #     ...

    # def test_refuses_insufficient_funds(self, api):
    #     ...

    def test_refuses_unknown_referenced_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=RandomGenerator.uuid(),
        )
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 404
        assert response["code"] == "RNV001016"


    def test_refuses_already_settled_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = api.post("/ledger/transactions", body=receipt, headers=headers)
        receipt_key = receipt_response["transaction_key"]

        first_settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, _ = api.post("/ledger/transactions", body=first_settlement, headers=headers)
        assert status == 201

        second_settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, response = api.post("/ledger/transactions", body=second_settlement, headers=headers)
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_replay_returns_200(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload()
        _, first_response = api.post("/ledger/transactions", body=payload, headers=headers)

        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 200
        assert response["transaction_key"] == first_response["transaction_key"]

    def test_refuses_reused_key_with_other_content(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload()
        api.post("/ledger/transactions", body=payload, headers=headers)

        other_payload = PayloadGenerator.create_ledger_transaction_payload(
            idempotency_key=payload["idempotency_key"],
            entries=[
                {"account_code": "reserves", "debit_minor": 5000},
                {"account_code": "in_transit", "credit_minor": 5000},
            ],
        )
        status, response = api.post("/ledger/transactions", body=other_payload, headers=headers)
        assert status == 422
        assert response["code"] == "RNV001024"

    def test_refuses_already_reversed_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = api.post("/ledger/transactions", body=receipt, headers=headers)
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
        status, _ = api.post("/ledger/transactions", body=first_refund, headers=headers)
        assert status == 201

        second_refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=refund_entries,
        )
        status, response = api.post("/ledger/transactions", body=second_refund, headers=headers)
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_refuses_unknown_type(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(type="banana")
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_zero_amount(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 0},
                {"account_code": "in_transit", "credit_minor": 0},
            ]
        )
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_negative_amount(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": -10000},
                {"account_code": "in_transit", "credit_minor": -10000},
            ]
        )
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_entry_with_debit_and_credit(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 10000, "credit_minor": 10000},
                {"account_code": "in_transit", "debit_minor": 10000, "credit_minor": 10000},
            ]
        )
        status, response = api.post("/ledger/transactions", body=payload, headers=headers)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_concurrent_replays_create_one_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        payload = PayloadGenerator.create_ledger_transaction_payload()

        def send(_):
            return api.post("/ledger/transactions", body=payload, headers=headers)

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(send, range(10)))

        statuses = sorted(status for status, _ in results)
        keys = {response["transaction_key"] for _, response in results}
        assert statuses == [200] * 9 + [201]
        assert len(keys) == 1

    def test_refuses_settling_reversed_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = api.post("/ledger/transactions", body=receipt, headers=headers)
        receipt_key = receipt_response["transaction_key"]

        refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        status, _ = api.post("/ledger/transactions", body=refund, headers=headers)
        assert status == 201

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, response = api.post("/ledger/transactions", body=settlement, headers=headers)
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_refuses_reversing_settled_transaction(self, api):
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = api.post("/ledger/transactions", body=receipt, headers=headers)
        receipt_key = receipt_response["transaction_key"]

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_key,
        )
        status, _ = api.post("/ledger/transactions", body=settlement, headers=headers)
        assert status == 201

        refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund",
            reverses_transaction_key=receipt_key,
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        status, response = api.post("/ledger/transactions", body=refund, headers=headers)
        assert status == 409
        assert response["code"] == "RNV001014"
    

   