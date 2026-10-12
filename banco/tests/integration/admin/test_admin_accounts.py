import pytest

from tests.utils.random_generator import RandomGenerator

ROUTE = "/admin/accounts"
PAGE_FIELDS = {"data", "limit", "cursor", "is_last_page"}


class TestAdminAccounts:
    def test_returns_a_page(self, admin, admin_token, active_account):
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert set(response) == PAGE_FIELDS

    def test_newest_account_comes_first_as_its_owner_sees_it(
        self, admin, admin_token, accounts, active_account, client_token
    ):
        _, owner_view = accounts.get_account(active_account, client_token)

        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert response["data"][0] == owner_view

    def test_lists_accounts_of_every_client(
        self, admin, admin_token, open_account, client_token, other_client_token
    ):
        first = open_account(client_token)
        second = open_account(other_client_token)

        status, response = admin.get(ROUTE, admin_token, {"limit": 2})
        assert status == 200
        assert [account["account_key"] for account in response["data"]] == [second, first]

    def test_does_not_list_internal_accounts(self, admin, admin_token, internal_accounts):
        status, internal = internal_accounts.list_internal_accounts()
        assert status == 200
        internal_keys = {account["account_key"] for account in internal}

        listed_keys = set()
        params = {"limit": 100}
        while True:
            status, response = admin.get(ROUTE, admin_token, params)
            assert status == 200
            listed_keys.update(account["account_key"] for account in response["data"])
            if response["is_last_page"]:
                break
            params = {"limit": 100, "cursor": response["cursor"]}

        assert listed_keys.isdisjoint(internal_keys)

    @pytest.mark.parametrize("status_filter", ["active", "rejected", "blocked", "closed"])
    def test_filters_by_status(
        self, admin, admin_token, accounts, open_account, client_token, internal_token, status_filter
    ):
        account_key = self._account_in_status(accounts, open_account, client_token, internal_token, status_filter)

        status, response = admin.get(ROUTE, admin_token, {"status": status_filter})
        assert status == 200
        assert response["data"][0]["account_key"] == account_key
        assert {account["status"] for account in response["data"]} == {status_filter}

    def test_status_filter_and_cursor_work_together(
        self, admin, admin_token, open_account, client_token
    ):
        rejected = [open_account(client_token, RandomGenerator.cnpj_rejected_by_bureau()) for _ in range(2)]
        open_account(client_token)

        status, first_page = admin.get(ROUTE, admin_token, {"status": "rejected", "limit": 1})
        assert status == 200
        status, second_page = admin.get(
            ROUTE, admin_token, {"status": "rejected", "limit": 1, "cursor": first_page["cursor"]}
        )
        assert status == 200
        assert [first_page["data"][0]["account_key"], second_page["data"][0]["account_key"]] == rejected[::-1]

    def test_cursor_walks_the_pages_without_repeating_or_skipping(
        self, admin, admin_token, open_account, client_token
    ):
        created_keys = [open_account(client_token) for _ in range(3)]

        seen = []
        params = {"limit": 1}
        for _ in range(3):
            status, response = admin.get(ROUTE, admin_token, params)
            assert status == 200
            seen.extend(account["account_key"] for account in response["data"])
            params = {"limit": 1, "cursor": response["cursor"]}

        assert seen == list(reversed(created_keys))

    @pytest.mark.parametrize(
        "params, code",
        [
            ({"status": "banana"}, "RNV000009"),
            ({"status": ""}, "RNV000009"),
            ({"limit": "0"}, "RNV000009"),
            ({"cursor": RandomGenerator.uuid()}, "RNV000011"),
            ({"cursor": "x"}, "RNV000011"),
            ({"cursor": ""}, "RNV000011"),
            ({"pagina": "2"}, "RNV000008"),
        ],
        ids=["unknown_status", "empty_status", "limit_zero", "public_key_cursor", "malformed_cursor", "empty_cursor", "unknown_parameter"],
    )
    def test_refuses_invalid_query(self, admin, admin_token, params, code):
        status, response = admin.get(ROUTE, admin_token, params)
        assert status == 400
        assert response["code"] == code

    def test_unknown_parameter_error_points_to_the_query(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token, {"order": "asc"})
        assert status == 400
        assert "query: " in response["description"]
        assert "body" not in response["description"]

    @staticmethod
    def _account_in_status(accounts, open_account, client_token, internal_token, status_filter) -> str:
        if status_filter == "rejected":
            return open_account(client_token, RandomGenerator.cnpj_rejected_by_bureau())
        account_key = open_account(client_token)
        if status_filter == "blocked":
            status, _ = accounts.block(account_key, internal_token)
            assert status == 200
        if status_filter == "closed":
            status, _ = accounts.close(account_key, client_token)
            assert status == 200
        return account_key
