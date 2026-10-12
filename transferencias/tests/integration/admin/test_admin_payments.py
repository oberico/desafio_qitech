from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tests.utils.random_generator import RandomGenerator

ROUTE = "/admin/payments"
PAGE_FIELDS = {"data", "limit", "cursor", "is_last_page"}
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


def walk(admin, admin_token, params: dict) -> list:
    pages = []
    query = dict(params)
    while True:
        status, response = admin.get(ROUTE, admin_token, query)
        assert status == 200
        pages.append(response)
        if response["is_last_page"]:
            return pages
        query = {**params, "cursor": response["cursor"]}


class TestAdminPayments:
    def test_returns_a_page_with_the_payment_dto(self, admin, admin_token, merchant, create_payments):
        created = create_payments(merchant, 1)

        status, response = admin.get(ROUTE, admin_token)

        assert status == 200
        assert set(response) == PAGE_FIELDS
        assert set(response["data"][0]) == PAYMENT_FIELDS
        assert keys_of(response)[0] == created[0]
        _, single = merchant.get_payment(created[0])
        assert response["data"][0] == single

    def test_lists_payments_of_every_client(self, admin, admin_token, merchant, other_merchant, create_payments):
        mine = create_payments(merchant, 2)
        theirs = create_payments(other_merchant, 2)

        _, response = admin.get(ROUTE, admin_token, {"limit": 4})

        assert set(keys_of(response)) == set(mine) | set(theirs)

    def test_lists_newest_first_across_clients(self, admin, admin_token, merchant, other_merchant, create_payments):
        first = create_payments(merchant, 1)
        second = create_payments(other_merchant, 1)
        third = create_payments(merchant, 1)

        _, response = admin.get(ROUTE, admin_token, {"limit": 3})

        assert keys_of(response) == [third[0], second[0], first[0]]

    def test_cursor_walks_every_page_without_repeating_or_skipping(
        self, admin, admin_token, merchant, create_company, create_payments
    ):
        company_key = create_company(merchant)
        created = create_payments(merchant, 5, company_key)

        pages = walk(admin, admin_token, {"company_key": company_key, "limit": 2})

        assert [len(page["data"]) for page in pages] == [2, 2, 1]
        assert [key for page in pages for key in keys_of(page)] == list(reversed(created))

    def test_page_that_is_not_the_last_has_an_opaque_cursor(self, admin, admin_token, merchant, create_payments):
        created = create_payments(merchant, 3)

        _, response = admin.get(ROUTE, admin_token, {"limit": 2})

        assert response["is_last_page"] is False
        assert response["limit"] == 2
        assert response["cursor"] is not None
        assert response["cursor"] not in created

    def test_last_page_has_no_cursor(self, admin, admin_token, merchant, create_company, create_payments):
        company_key = create_company(merchant)
        create_payments(merchant, 2, company_key)

        _, response = admin.get(ROUTE, admin_token, {"company_key": company_key, "limit": 2})

        assert response["is_last_page"] is True
        assert response["cursor"] is None

    def test_default_limit_is_twenty(self, admin, admin_token, merchant, create_payments):
        create_payments(merchant, 21)

        _, response = admin.get(ROUTE, admin_token)

        assert response["limit"] == 20
        assert len(response["data"]) == 20
        assert response["is_last_page"] is False

    def test_accepts_the_maximum_limit(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token, {"limit": 100})

        assert status == 200
        assert response["limit"] == 100

    def test_empty_list_for_company_without_payments(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token, {"company_key": RandomGenerator.uuid()})

        assert status == 200
        assert response == {"data": [], "limit": 20, "cursor": None, "is_last_page": True}

    def test_filters_by_company_key(self, admin, admin_token, merchant, other_merchant, create_company, create_payments):
        company_key = create_company(merchant)
        mine = create_payments(merchant, 2, company_key)
        create_payments(other_merchant, 2)

        _, response = admin.get(ROUTE, admin_token, {"company_key": company_key})

        assert keys_of(response) == list(reversed(mine))
        assert {item["company_key"] for item in response["data"]} == {company_key}

    def test_filters_by_held_status(self, admin, admin_token, merchant, create_company, create_payments):
        company_key = create_company(merchant)
        created = create_payments(merchant, 2, company_key)
        merchant.refund_payment(created[0])

        _, response = admin.get(ROUTE, admin_token, {"company_key": company_key, "status": "held"})

        assert keys_of(response) == [created[1]]

    def test_filters_by_refunded_status(self, admin, admin_token, merchant, create_company, create_payments):
        company_key = create_company(merchant)
        created = create_payments(merchant, 2, company_key)
        merchant.refund_payment(created[0])

        _, response = admin.get(ROUTE, admin_token, {"company_key": company_key, "status": "refunded"})

        assert keys_of(response) == [created[0]]
        assert response["data"][0]["status"] == "refunded"

    def test_filters_by_settled_status(
        self, admin, admin_token, merchant, create_company, create_payments, settlements
    ):
        company_key = create_company(merchant)
        created = create_payments(merchant, 2, company_key)
        _, payment = merchant.get_payment(created[0])
        as_of = (datetime.fromisoformat(payment["release_at"]) + timedelta(seconds=1)).isoformat()
        status, _ = settlements.run(as_of)
        assert status == 200

        _, response = admin.get(ROUTE, admin_token, {"company_key": company_key, "status": "settled"})

        assert created[0] in keys_of(response)
        assert {item["status"] for item in response["data"]} == {"settled"}

    def test_status_filter_alone_spans_clients(self, admin, admin_token, merchant, other_merchant, create_payments):
        mine = create_payments(merchant, 1)
        theirs = create_payments(other_merchant, 1)
        merchant.refund_payment(mine[0])
        other_merchant.refund_payment(theirs[0])

        _, response = admin.get(ROUTE, admin_token, {"status": "refunded", "limit": 2})

        assert keys_of(response) == [theirs[0], mine[0]]

    def test_status_company_and_cursor_work_together(
        self, admin, admin_token, merchant, create_company, create_payments
    ):
        company_key = create_company(merchant)
        created = create_payments(merchant, 4, company_key)
        merchant.refund_payment(created[1])

        pages = walk(admin, admin_token, {"company_key": company_key, "status": "held", "limit": 1})

        assert [key for page in pages for key in keys_of(page)] == [created[3], created[2], created[0]]

    @pytest.mark.parametrize("limit", ["0", "101", "-1", "abc", "1.5", "", "007"])
    def test_refuses_invalid_limit(self, admin, admin_token, limit):
        status, response = admin.get(ROUTE, admin_token, {"limit": limit})

        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("value", ["banana", "", "HELD"])
    def test_refuses_invalid_status(self, admin, admin_token, value):
        status, response = admin.get(ROUTE, admin_token, {"status": value})

        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("value", ["not-a-uuid", "", "123"])
    def test_refuses_invalid_company_key(self, admin, admin_token, value):
        status, response = admin.get(ROUTE, admin_token, {"company_key": value})

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_unknown_parameter(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token, {"page": "2"})

        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize(
        "cursor",
        [RandomGenerator.uuid(), "x", "not-a-cursor", ""],
        ids=["invented_cursor", "malformed_cursor", "text_cursor", "empty_cursor"],
    )
    def test_refuses_invalid_cursor(self, admin, admin_token, cursor):
        status, response = admin.get(ROUTE, admin_token, {"cursor": cursor})

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_tampered_cursor(self, admin, admin_token, merchant, create_payments):
        create_payments(merchant, 2)
        _, first_page = admin.get(ROUTE, admin_token, {"limit": 1})
        cursor = first_page["cursor"]
        tampered = ("B" if cursor[0] == "A" else "A") + cursor[1:]

        status, response = admin.get(ROUTE, admin_token, {"limit": 1, "cursor": tampered})

        assert status == 400
        assert response["code"] == "RNV000001"
