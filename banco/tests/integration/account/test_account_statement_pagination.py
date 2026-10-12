from datetime import datetime, timedelta, timezone

import pytest


INVALID_PARAMS = {
    "zero_limit": {"limit": 0},
    "limit_above_max": {"limit": 101},
    "text_limit": {"limit": "abc"},
    "invented_cursor": {"cursor": "not-a-cursor"},
    "from_without_timezone": {"from": "2026-10-01T00:00:00"},
    "from_not_a_date": {"from": "yesterday"},
    "to_without_timezone": {"to": "2026-10-31T23:59:59"},
    "from_after_to": {"from": "2026-10-31T00:00:00-03:00", "to": "2026-10-01T00:00:00-03:00"},
    "unknown_param": {"offset": 1},
}


class TestAccountStatementPagination:
    def test_limit_returns_first_page_with_cursor(self, accounts, active_account, client_token, credit_account):
        credit_account(active_account, 1000)
        newest = credit_account(active_account, 2000)

        status, response = accounts.get_statement(active_account, client_token, params={"limit": 1})

        assert status == 200
        assert [entry["transaction_key"] for entry in response["data"]] == [newest]
        assert response["limit"] == 1
        assert response["cursor"] is not None
        assert response["is_last_page"] is False

    def test_cursor_returns_next_page(self, accounts, active_account, client_token, credit_account):
        oldest = credit_account(active_account, 1000)
        credit_account(active_account, 2000)
        _, first_page = accounts.get_statement(active_account, client_token, params={"limit": 1})

        status, response = accounts.get_statement(
            active_account, client_token, params={"limit": 1, "cursor": first_page["cursor"]}
        )

        assert status == 200
        assert [entry["transaction_key"] for entry in response["data"]] == [oldest]
        assert response["cursor"] is None
        assert response["is_last_page"] is True

    def test_date_filter_keeps_entries_inside_the_range(self, accounts, active_account, client_token, credit_account):
        transaction_key = credit_account(active_account, 1000)
        now = datetime.now(timezone.utc)
        params = {"from": (now - timedelta(days=1)).isoformat(), "to": (now + timedelta(days=1)).isoformat()}

        status, response = accounts.get_statement(active_account, client_token, params=params)

        assert status == 200
        assert [entry["transaction_key"] for entry in response["data"]] == [transaction_key]

    @pytest.mark.parametrize("days_from, days_to",[(1, 2), (-2, -1)],
        ids=["range_in_the_future", "range_in_the_past"],
    )
    def test_date_filter_drops_entries_outside_the_range(self, accounts, active_account, client_token, credit_account, days_from, days_to):
        credit_account(active_account, 1000)
        now = datetime.now(timezone.utc)
        params = {"from": (now + timedelta(days=days_from)).isoformat(), "to": (now + timedelta(days=days_to)).isoformat()}

        status, response = accounts.get_statement(active_account, client_token, params=params)

        assert status == 200
        assert response["data"] == []

    @pytest.mark.parametrize("params", INVALID_PARAMS.values(), ids=INVALID_PARAMS.keys())
    def test_refuses_invalid_pagination(self, accounts, active_account, client_token, params):
        status, response = accounts.get_statement(active_account, client_token, params=params)

        assert status == 400
        assert response["code"] == "RNV000001"

    def test_unknown_parameter_error_points_to_the_query(self, accounts, active_account, client_token):
        status, response = accounts.get_statement(active_account, client_token, params={"offset": 1})

        assert status == 400
        assert "query: " in response["description"]
        assert "body" not in response["description"]

    def test_refuses_tampered_cursor(self, accounts, active_account, client_token, credit_account):
        credit_account(active_account, 1000)
        credit_account(active_account, 2000)
        _, first_page = accounts.get_statement(active_account, client_token, params={"limit": 1})
        cursor = first_page["cursor"]
        tampered = ("B" if cursor[0] == "A" else "A") + cursor[1:]

        status, response = accounts.get_statement(active_account, client_token, params={"limit": 1, "cursor": tampered})

        assert status == 400
        assert response["code"] == "RNV000001"
