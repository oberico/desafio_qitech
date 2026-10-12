import pytest

from tests.utils.random_generator import RandomGenerator


READ_ROUTES = ["balance", "statement"]


class TestAccountReadAccess:
    @pytest.mark.parametrize("route", READ_ROUTES)
    @pytest.mark.parametrize(
        "headers",
        [None, {"Authorization": "Bearer token-que-nao-existe"}],
        ids=["missing_token", "unknown_token"],
    )
    def test_refuses_missing_or_unknown_token(self, api, active_account, route, headers):
        status, response = api.get(f"/accounts/{active_account}/{route}", headers=headers)

        assert status == 401
        assert response["code"] == "RNV000003"

    @pytest.mark.parametrize("route", READ_ROUTES)
    def test_account_of_another_client_looks_nonexistent(self, api, active_account, other_client_token, route):
        status, response = api.get(
            f"/accounts/{active_account}/{route}",
            headers={"Authorization": f"Bearer {other_client_token}"},
        )

        assert status == 404
        assert response["code"] == "RNV001021"

    @pytest.mark.parametrize("route", READ_ROUTES)
    @pytest.mark.parametrize("account_key", [RandomGenerator.uuid(), "x" * 36], ids=["nonexistent", "malformed"])
    def test_refuses_unknown_account(self, api, client_token, route, account_key):
        status, response = api.get(
            f"/accounts/{account_key}/{route}",
            headers={"Authorization": f"Bearer {client_token}"},
        )

        assert status == 404
        assert response["code"] == "RNV001021"

    @pytest.mark.parametrize("route", READ_ROUTES)
    def test_owner_can_still_read_a_blocked_account(self, api, blocked_account, client_token, route):
        status, _ = api.get(
            f"/accounts/{blocked_account}/{route}",
            headers={"Authorization": f"Bearer {client_token}"},
        )

        assert status == 200

    @pytest.mark.parametrize("route", READ_ROUTES)
    def test_owner_can_still_read_a_closed_account(self, api, accounts, active_account, client_token, route):
        status, _ = accounts.close(active_account, client_token)
        assert status == 200

        status, _ = api.get(
            f"/accounts/{active_account}/{route}",
            headers={"Authorization": f"Bearer {client_token}"},
        )

        assert status == 200