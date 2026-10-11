import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

BIGINT_MAX = 9223372036854775807
MAX_ENTRIES = 20


def entries_with_total(total: int) -> list:
    debits = total - 1
    entries = [{"account_code": "reserves", "debit_minor": 1} for _ in range(debits)]
    entries.append({"account_code": "in_transit", "credit_minor": debits})
    return entries


class TestLedgerAmountLimits:
    @pytest.mark.parametrize("amount", [BIGINT_MAX + 1, 10**30])
    def test_refuses_debit_above_bigint(self, ledger, amount):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": amount},
                {"account_code": "in_transit", "credit_minor": 10000},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("amount", [BIGINT_MAX + 1, 10**30])
    def test_refuses_credit_above_bigint(self, ledger, amount):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": amount},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("amount", [BIGINT_MAX + 1, 10**30])
    def test_refuses_balanced_entries_above_bigint(self, ledger, amount):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": amount},
                {"account_code": "in_transit", "credit_minor": amount},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_accepts_exact_bigint_limit(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": BIGINT_MAX},
                {"account_code": "in_transit", "credit_minor": BIGINT_MAX},
            ]
        )
        status, _ = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201


class TestLedgerEntriesLimit:
    def test_refuses_more_than_max_entries(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(entries=entries_with_total(MAX_ENTRIES + 1))
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_accepts_exactly_max_entries(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(entries=entries_with_total(MAX_ENTRIES))
        status, _ = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201
