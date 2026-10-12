from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tests.utils.random_generator import RandomGenerator

PAGE_FIELDS = {"data", "cursor", "is_last_page"}
PAYMENT_FIELDS = {
    "payment_key",
    "company_key",
    "account_key",
    "transaction_key",
    "method",
    "status",
    "amount_minor",
    "fee_bps",
    "release_at",
}


def keys_of(response: dict) -> list:
    return [payment["payment_key"] for payment in response["data"]]


def walk(merchant, params: dict) -> list:
    pages = []
    query = dict(params)
    while True:
        status, response = merchant.list_payments(query)
        assert status == 200
        pages.append(response)
        if response["is_last_page"]:
            return pages
        query = {**params, "cursor": response["cursor"]}


class TestPaymentList:
    def test_returns_a_page_with_the_payment_dto(self, merchant, create_payments):
        created = create_payments(merchant, 1)

        status, response = merchant.list_payments()

        assert status == 200
        assert set(response) == PAGE_FIELDS
        assert set(response["data"][0]) == PAYMENT_FIELDS
        assert keys_of(response) == created
        _, single = merchant.get_payment(created[0])
        assert response["data"][0] == single

    def test_lists_newest_first(self, merchant, create_payments):
        created = create_payments(merchant, 3)

        _, response = merchant.list_payments()

        assert keys_of(response) == list(reversed(created))

    def test_empty_list_for_client_without_payments(self, merchant):
        status, response = merchant.list_payments()

        assert status == 200
        assert response == {"data": [], "cursor": None, "is_last_page": True}

    def test_single_page_is_the_last_page(self, merchant, create_payments):
        create_payments(merchant, 2)

        _, response = merchant.list_payments({"limit": 2})

        assert response["is_last_page"] is True
        assert response["cursor"] is None

    def test_full_page_with_more_items_is_not_the_last_page(self, merchant, create_payments):
        created = create_payments(merchant, 3)

        _, response = merchant.list_payments({"limit": 2})

        assert response["is_last_page"] is False
        assert response["cursor"] == keys_of(response)[-1] == created[1]

    def test_cursor_walks_every_page_without_repeating_or_skipping(self, merchant, create_payments):
        created = create_payments(merchant, 5)

        pages = walk(merchant, {"limit": 2})

        assert [len(page["data"]) for page in pages] == [2, 2, 1]
        assert [key for page in pages for key in keys_of(page)] == list(reversed(created))

    def test_cursor_does_not_slip_when_a_payment_is_created_between_pages(self, merchant, create_payments):
        created = create_payments(merchant, 4)
        _, first_page = merchant.list_payments({"limit": 2})

        newcomer = create_payments(merchant, 1)

        _, second_page = merchant.list_payments({"limit": 2, "cursor": first_page["cursor"]})
        assert second_page["is_last_page"] is True
        assert keys_of(first_page) + keys_of(second_page) == list(reversed(created))
        _, fresh = merchant.list_payments({"limit": 1})
        assert keys_of(fresh) == newcomer

    def test_default_limit_is_twenty(self, merchant, create_payments):
        create_payments(merchant, 21)

        _, response = merchant.list_payments()

        assert len(response["data"]) == 20
        assert response["is_last_page"] is False

    def test_accepts_the_maximum_limit(self, merchant, create_payments):
        create_payments(merchant, 2)

        status, response = merchant.list_payments({"limit": 100})

        assert status == 200
        assert len(response["data"]) == 2

    @pytest.mark.parametrize("limit", ["0", "101", "-1", "abc", "1.5", "", "007"])
    def test_refuses_invalid_limit(self, merchant, limit):
        status, response = merchant.list_payments({"limit": limit})

        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize(
        "cursor",
        [RandomGenerator.uuid(), "x", ""],
        ids=["unknown_cursor", "malformed_cursor", "empty_cursor"],
    )
    def test_refuses_invalid_cursor(self, merchant, create_payments, cursor):
        create_payments(merchant, 1)

        status, response = merchant.list_payments({"cursor": cursor})

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_cursor_of_another_clients_payment(self, merchant, other_merchant, create_payments):
        foreign = create_payments(other_merchant, 1)

        status, response = merchant.list_payments({"cursor": foreign[0]})

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_unknown_parameter(self, merchant):
        status, response = merchant.list_payments({"page": "2"})

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_filters_by_held_status(self, merchant, create_payments):
        created = create_payments(merchant, 2)
        merchant.refund_payment(created[0])

        _, response = merchant.list_payments({"status": "held"})

        assert keys_of(response) == [created[1]]

    def test_filters_by_refunded_status(self, merchant, create_payments):
        created = create_payments(merchant, 2)
        merchant.refund_payment(created[0])

        _, response = merchant.list_payments({"status": "refunded"})

        assert keys_of(response) == [created[0]]
        assert response["data"][0]["status"] == "refunded"

    def test_filters_by_settled_status(self, merchant, create_payments, settlements):
        created = create_payments(merchant, 2)
        _, payment = merchant.get_payment(created[0])
        as_of = (datetime.fromisoformat(payment["release_at"]) + timedelta(seconds=1)).isoformat()
        status, _ = settlements.run(as_of)
        assert status == 200

        _, response = merchant.list_payments({"status": "settled"})

        assert created[0] in keys_of(response)
        assert {item["status"] for item in response["data"]} == {"settled"}

    def test_status_filter_and_cursor_work_together(self, merchant, create_payments):
        created = create_payments(merchant, 4)
        merchant.refund_payment(created[1])

        pages = walk(merchant, {"status": "held", "limit": 1})

        assert [key for page in pages for key in keys_of(page)] == [created[3], created[2], created[0]]

    @pytest.mark.parametrize("value", ["banana", "", "HELD"])
    def test_refuses_invalid_status(self, merchant, value):
        status, response = merchant.list_payments({"status": value})

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_never_lists_payments_of_another_client(self, merchant, other_merchant, create_payments):
        mine = create_payments(merchant, 2)
        theirs = create_payments(other_merchant, 2)

        _, my_page = merchant.list_payments()
        _, their_page = other_merchant.list_payments()

        assert keys_of(my_page) == list(reversed(mine))
        assert keys_of(their_page) == list(reversed(theirs))

    def test_lists_payments_of_every_company_of_the_client(self, merchant, create_company, create_payments):
        first_company = create_company(merchant)
        second_company = create_company(merchant)
        first = create_payments(merchant, 1, first_company)
        second = create_payments(merchant, 1, second_company)

        _, response = merchant.list_payments()

        assert keys_of(response) == [second[0], first[0]]
        assert {item["company_key"] for item in response["data"]} == {first_company, second_company}
