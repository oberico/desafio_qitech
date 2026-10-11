from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.utils.ledger_requests import REFERENCE_FIELD
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

    def test_refuses_inactive_account(self, ledger, accounts, open_account, client_token):
        account_key = open_account(client_token)
        accounts.close(account_key, client_token)

        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_response["transaction_key"],
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_key": account_key, "credit_minor": 10000},
            ],
        )
        status, response = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 422
        assert response["code"] == "RNV001005"

    def test_refuses_insufficient_funds(self, ledger, active_account):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ],
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 422
        assert response["code"] == "RNV001006"

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

    @pytest.mark.parametrize(
        "type, references",
        [
            ("settlement", {}),
            ("settlement", {"reverses_transaction_key": RandomGenerator.uuid()}),
            (
                "settlement",
                {
                    "settles_transaction_key": RandomGenerator.uuid(),
                    "reverses_transaction_key": RandomGenerator.uuid(),
                },
            ),
            ("refund", {}),
            ("refund", {"settles_transaction_key": RandomGenerator.uuid()}),
            ("reversal", {}),
            ("reversal", {"settles_transaction_key": RandomGenerator.uuid()}),
            ("receipt", {"settles_transaction_key": RandomGenerator.uuid()}),
            ("receipt", {"reverses_transaction_key": RandomGenerator.uuid()}),
            ("payout", {"settles_transaction_key": RandomGenerator.uuid()}),
            ("payout", {"reverses_transaction_key": RandomGenerator.uuid()}),
        ],
        ids=[
            "settlement_without_reference",
            "settlement_with_reverses",
            "settlement_with_both_references",
            "refund_without_reference",
            "refund_with_settles",
            "reversal_without_reference",
            "reversal_with_settles",
            "receipt_with_settles",
            "receipt_with_reverses",
            "payout_with_settles",
            "payout_with_reverses",
        ],
    )
    def test_refuses_references_that_do_not_match_type(self, ledger, type, references):
        payload = PayloadGenerator.create_ledger_transaction_payload(type=type, **references)
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize(
        "type, target_type",
        [
            ("settlement", "refund"),
            ("settlement", "reversal"),
            ("settlement", "settlement"),
            ("refund", "payout"),
            ("refund", "refund"),
            ("refund", "settlement"),
            ("reversal", "receipt"),
            ("reversal", "reversal"),
            ("reversal", "settlement"),
        ],
    )
    def test_refuses_reference_to_wrong_transaction_type(self, ledger, type, target_type):
        target_key = ledger.create_transaction(target_type)
        payload = PayloadGenerator.create_ledger_transaction_payload(type=type, **{REFERENCE_FIELD[type]: target_key})
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 422
        assert response["code"] == "RNV001033"

    @pytest.mark.parametrize("type, target_type", [("settlement", "receipt"), ("settlement", "payout"), ("refund", "receipt"), ("reversal", "payout")])
    def test_accepts_reference_to_matching_transaction_type(self, ledger, type, target_type):
        target_key = ledger.create_transaction(target_type)
        payload = PayloadGenerator.create_ledger_transaction_payload(type=type, **{REFERENCE_FIELD[type]: target_key})
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201
        assert response["type"] == type

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

    def test_concurrent_debits_never_overdraw(self, ledger, active_account):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_response["transaction_key"],
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_key": active_account, "credit_minor": 10000},
            ],
        )
        status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 201

        payout = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ],
        )

        def send(_):
            return ledger.post_transaction(payout, RandomGenerator.uuid())

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(send, range(2)))

        statuses = sorted(status for status, _ in results)
        refused = [response["code"] for status, response in results if status == 422]
        assert statuses == [201, 422]
        assert refused == ["RNV001006"]

    def test_payout_is_born_pending(self, ledger, active_account):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_response["transaction_key"],
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_key": active_account, "credit_minor": 10000},
            ],
        )
        status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 201

        payout = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ],
        )
        status, response = ledger.post_transaction(payout, RandomGenerator.uuid())
        assert status == 201
        assert response["type"] == "payout"
        assert response["status"] == "pending"

    @pytest.mark.parametrize("amount", ["10000", 100.5, 10000.0], ids=["text", "decimal", "whole_decimal"])
    def test_refuses_non_integer_amount(self, ledger, amount):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": amount},
                {"account_code": "in_transit", "credit_minor": amount},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"