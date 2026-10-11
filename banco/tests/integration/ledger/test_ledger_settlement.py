from concurrent.futures import ThreadPoolExecutor

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestLedgerSettlement:
    def test_settlement_is_born_settled(self, ledger):
        payout_key = ledger.create_transaction("payout")
        payload = PayloadGenerator.create_ledger_transaction_payload(type="settlement", settles_transaction_key=payout_key)
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201
        assert response["status"] == "settled"

    def test_settling_payout_moves_it_to_settled(self, ledger):
        idempotency_key = RandomGenerator.uuid()
        payout = PayloadGenerator.create_ledger_transaction_payload(type="payout")
        _, created = ledger.post_transaction(payout, idempotency_key)
        assert created["status"] == "pending"

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement", settles_transaction_key=created["transaction_key"]
        )
        status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 201

        status, replayed = ledger.post_transaction(payout, idempotency_key)
        assert status == 200
        assert replayed["status"] == "settled"

    def test_settling_receipt_keeps_it_settled(self, ledger):
        idempotency_key = RandomGenerator.uuid()
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        _, created = ledger.post_transaction(receipt, idempotency_key)

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement", settles_transaction_key=created["transaction_key"]
        )
        ledger.post_transaction(settlement, RandomGenerator.uuid())

        _, replayed = ledger.post_transaction(receipt, idempotency_key)
        assert replayed["status"] == "settled"

    def test_reversing_payout_keeps_it_pending(self, ledger):
        idempotency_key = RandomGenerator.uuid()
        payout = PayloadGenerator.create_ledger_transaction_payload(type="payout")
        _, created = ledger.post_transaction(payout, idempotency_key)

        reversal = PayloadGenerator.create_ledger_transaction_payload(
            type="reversal",
            reverses_transaction_key=created["transaction_key"],
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        status, _ = ledger.post_transaction(reversal, RandomGenerator.uuid())
        assert status == 201

        _, replayed = ledger.post_transaction(payout, idempotency_key)
        assert replayed["status"] == "pending"

    def test_refuses_settling_payout_twice(self, ledger):
        payout_key = ledger.create_transaction("payout")
        first = PayloadGenerator.create_ledger_transaction_payload(type="settlement", settles_transaction_key=payout_key)
        status, _ = ledger.post_transaction(first, RandomGenerator.uuid())
        assert status == 201

        second = PayloadGenerator.create_ledger_transaction_payload(type="settlement", settles_transaction_key=payout_key)
        status, response = ledger.post_transaction(second, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_refuses_reversing_settled_payout(self, ledger):
        payout_key = ledger.create_transaction("payout")
        settlement = PayloadGenerator.create_ledger_transaction_payload(type="settlement", settles_transaction_key=payout_key)
        ledger.post_transaction(settlement, RandomGenerator.uuid())

        reversal = PayloadGenerator.create_ledger_transaction_payload(
            type="reversal",
            reverses_transaction_key=payout_key,
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        status, response = ledger.post_transaction(reversal, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_refuses_settling_reversed_payout(self, ledger):
        payout_key = ledger.create_transaction("payout")
        reversal = PayloadGenerator.create_ledger_transaction_payload(
            type="reversal",
            reverses_transaction_key=payout_key,
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_code": "reserves", "credit_minor": 10000},
            ],
        )
        ledger.post_transaction(reversal, RandomGenerator.uuid())

        settlement = PayloadGenerator.create_ledger_transaction_payload(type="settlement", settles_transaction_key=payout_key)
        status, response = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 409
        assert response["code"] == "RNV001014"

    def test_concurrent_settlements_settle_payout_once(self, ledger):
        payout_key = ledger.create_transaction("payout")
        settlement = PayloadGenerator.create_ledger_transaction_payload(type="settlement", settles_transaction_key=payout_key)

        def settle(_):
            return ledger.post_transaction(settlement, RandomGenerator.uuid())

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(settle, range(8)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [201] + [409] * 7
        assert {response["code"] for status, response in results if status == 409} == {"RNV001014"}
