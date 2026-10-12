from concurrent.futures import ThreadPoolExecutor

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


def fund(ledger, account_key: str, amount: int) -> None:
    receipt = PayloadGenerator.create_ledger_transaction_payload(
        entries=[
            {"account_code": "reserves", "debit_minor": amount},
            {"account_code": "in_transit", "credit_minor": amount},
        ]
    )
    _, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
    settlement = PayloadGenerator.create_ledger_transaction_payload(
        type="settlement",
        settles_transaction_key=receipt_response["transaction_key"],
        entries=[
            {"account_code": "in_transit", "debit_minor": amount},
            {"account_key": account_key, "credit_minor": amount},
        ],
    )
    status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
    assert status == 201


class TestLedgerLockOrdering:
    def test_opposite_order_debits_never_deadlock(self, ledger, open_account, client_token, other_client_token):
        account_a = open_account(client_token)
        account_b = open_account(other_client_token)
        fund(ledger, account_a, 1000)
        fund(ledger, account_b, 1000)
        debit_a = {"account_key": account_a, "debit_minor": 1}
        debit_b = {"account_key": account_b, "debit_minor": 1}
        credit = {"account_code": "in_transit", "credit_minor": 2}

        def send(index):
            debits = [debit_a, debit_b] if index % 2 == 0 else [debit_b, debit_a]
            payload = PayloadGenerator.create_ledger_transaction_payload(type="payout", entries=debits + [credit])
            return ledger.post_transaction(payload, RandomGenerator.uuid())

        with ThreadPoolExecutor(max_workers=50) as executor:
            results = list(executor.map(send, range(100)))

        assert [status for status, _ in results] == [201] * 100


class TestLedgerDuplicateDebits:
    def _payout(self, ledger, account_key: str, amounts: list) -> tuple:
        entries = [{"account_key": account_key, "debit_minor": amount} for amount in amounts]
        entries.append({"account_code": "in_transit", "credit_minor": sum(amounts)})
        payload = PayloadGenerator.create_ledger_transaction_payload(type="payout", entries=entries)
        return ledger.post_transaction(payload, RandomGenerator.uuid())

    def test_refuses_duplicate_debits_exceeding_balance(self, ledger, active_account):
        fund(ledger, active_account, 100)
        status, response = self._payout(ledger, active_account, [60, 60])
        assert status == 422
        assert response["code"] == "RNV001006"

    def test_accepts_duplicate_debits_within_balance(self, ledger, active_account):
        fund(ledger, active_account, 100)
        status, _ = self._payout(ledger, active_account, [40, 40])
        assert status == 201
