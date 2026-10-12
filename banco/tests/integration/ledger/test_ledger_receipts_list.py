from datetime import datetime, timedelta, timezone

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

PAGE_FIELDS = {"data", "limit", "cursor", "is_last_page"}
ITEM_FIELDS = {"transaction_key", "idempotency_key", "amount_minor", "created_at"}


def instant(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def post_receipt(ledger, amount_minor: int = 10000) -> tuple:
    key = RandomGenerator.uuid()
    payload = PayloadGenerator.create_ledger_transaction_payload(
        entries=[
            {"account_code": "reserves", "debit_minor": amount_minor},
            {"account_code": "in_transit", "credit_minor": amount_minor},
        ]
    )
    status, response = ledger.post_transaction(payload, key)
    assert status == 201, f"não deu para lançar o recebimento: {status} {response}"
    return key, response["transaction_key"]


def listed_keys(ledger, params: dict) -> list:
    status, response = ledger.list_receipts(params)
    assert status == 200, f"não deu para listar os recebimentos: {status} {response}"
    return [item["transaction_key"] for item in response["data"]]


class TestLedgerReceiptsList:
    @pytest.mark.parametrize(
        "headers",
        [{}, {"INTERNAL-TOKEN": "wrong-token"}],
        ids=["without_token", "wrong_token"],
    )
    def test_refuses_without_the_internal_token(self, ledger, headers):
        status, response = ledger.list_receipts({"before": instant(5)}, headers)
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_lists_an_open_receipt_with_its_amount(self, ledger):
        key, transaction_key = post_receipt(ledger, 1234)

        status, response = ledger.list_receipts({"before": instant(5)})

        assert status == 200
        assert set(response) == PAGE_FIELDS
        item = next(item for item in response["data"] if item["transaction_key"] == transaction_key)
        assert set(item) == ITEM_FIELDS
        assert item["idempotency_key"] == key
        assert item["amount_minor"] == 1234

    def test_newest_receipt_comes_first(self, ledger):
        _, older = post_receipt(ledger)
        _, newer = post_receipt(ledger)

        keys = listed_keys(ledger, {"before": instant(5), "limit": 2})

        assert keys == [newer, older]

    def test_does_not_list_a_receipt_created_after_the_cutoff(self, ledger):
        cutoff = instant(-60)
        _, transaction_key = post_receipt(ledger)

        status, response = ledger.list_receipts({"before": cutoff})

        assert status == 200
        assert transaction_key not in [item["transaction_key"] for item in response["data"]]
        assert all(item["created_at"] < cutoff for item in response["data"])

    def test_does_not_list_a_settled_receipt(self, ledger):
        _, transaction_key = post_receipt(ledger)
        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement", settles_transaction_key=transaction_key
        )
        status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 201

        assert transaction_key not in listed_keys(ledger, {"before": instant(5)})

    def test_does_not_list_a_refunded_receipt(self, ledger):
        _, transaction_key = post_receipt(ledger)
        refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund", reverses_transaction_key=transaction_key
        )
        status, _ = ledger.post_transaction(refund, RandomGenerator.uuid())
        assert status == 201

        assert transaction_key not in listed_keys(ledger, {"before": instant(5)})

    def test_does_not_list_other_transaction_types(self, ledger):
        payout_key = ledger.create_transaction("payout")

        assert payout_key not in listed_keys(ledger, {"before": instant(5)})

    def test_cursor_walks_to_the_next_page(self, ledger):
        _, older = post_receipt(ledger)
        _, newer = post_receipt(ledger)

        status, first_page = ledger.list_receipts({"before": instant(5), "limit": 1})
        assert status == 200
        assert first_page["is_last_page"] is False

        status, second_page = ledger.list_receipts({"before": instant(5), "limit": 1, "cursor": first_page["cursor"]})
        assert status == 200
        assert [item["transaction_key"] for item in first_page["data"]] == [newer]
        assert [item["transaction_key"] for item in second_page["data"]] == [older]

    @pytest.mark.parametrize(
        "params, code",
        [
            ({}, "RNV000007"),
            ({"before": "2026-10-12T00:00:00"}, "RNV000009"),
            ({"before": "amanha"}, "RNV000009"),
            ({"before": "2026-10-12T00:00:00Z", "limit": "0"}, "RNV000009"),
            ({"before": "2026-10-12T00:00:00Z", "cursor": "x"}, "RNV000011"),
            ({"before": "2026-10-12T00:00:00Z", "pagina": "2"}, "RNV000008"),
        ],
        ids=["missing_before", "before_without_timezone", "before_not_a_date", "limit_zero", "invalid_cursor", "unknown_parameter"],
    )
    def test_refuses_invalid_query(self, ledger, params, code):
        status, response = ledger.list_receipts(params)
        assert status == 400
        assert response["code"] == code
