import pytest


INVALID_PARAMS = {
    "zero_limit": {"limit": 0},
    "limit_above_max": {"limit": 101},
    "text_limit": {"limit": "abc"},
    "negative_offset": {"offset": -1},
    "text_offset": {"offset": "abc"},
    "unknown_param": {"page": 1},
}


class TestAccountStatementPagination:
    def test_limit_returns_first_page_with_more_to_come(self, accounts, active_account, client_token, credit_account):
        credit_account(active_account, 1000)
        newest = credit_account(active_account, 2000)

        status, response = accounts.get_statement(active_account, client_token, params={"limit": 1})

        assert status == 200
        assert [entry["transaction_key"] for entry in response["entries"]] == [newest]
        assert response["has_more"] is True

    def test_offset_returns_next_page(self, accounts, active_account, client_token, credit_account):
        oldest = credit_account(active_account, 1000)
        credit_account(active_account, 2000)

        status, response = accounts.get_statement(active_account, client_token, params={"limit": 1, "offset": 1})

        assert status == 200
        assert [entry["transaction_key"] for entry in response["entries"]] == [oldest]
        assert response["has_more"] is False

    @pytest.mark.parametrize("params", INVALID_PARAMS.values(), ids=INVALID_PARAMS.keys())
    def test_refuses_invalid_pagination(self, accounts, active_account, client_token, params):
        status, response = accounts.get_statement(active_account, client_token, params=params)

        assert status == 400
        assert response["code"] == "RNV000001"
