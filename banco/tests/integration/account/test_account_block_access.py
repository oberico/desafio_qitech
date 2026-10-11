import pytest

from tests.utils.random_generator import RandomGenerator


class TestAccountBlockAccess:
    @pytest.mark.parametrize("internal_token", [None, "wrong-token"], ids=["missing_token", "wrong_token"])
    def test_block_refuses_missing_or_wrong_internal_token(self, accounts, active_account, internal_token):
        status, response = accounts.block(active_account, internal_token)

        assert status == 403
        assert response["code"] == "RNV000002"

    @pytest.mark.parametrize("internal_token", [None, "wrong-token"], ids=["missing_token", "wrong_token"])
    def test_unblock_refuses_missing_or_wrong_internal_token(self, accounts, active_account, internal_token):
        status, response = accounts.unblock(active_account, internal_token)

        assert status == 403
        assert response["code"] == "RNV000002"

    @pytest.mark.parametrize("action", ["block", "unblock"])
    def test_client_token_does_not_replace_internal_token(self, api, active_account, client_token, action):
        status, response = api.post(
            f"/internal/accounts/{active_account}/{action}",
            headers={"Authorization": f"Bearer {client_token}"},
        )

        assert status == 403
        assert response["code"] == "RNV000002"

    @pytest.mark.parametrize("action", ["block", "unblock"])
    @pytest.mark.parametrize("account_key", [RandomGenerator.uuid(), "x" * 36], ids=["nonexistent", "malformed"])
    def test_refuses_unknown_account(self, api, internal_token, action, account_key):
        status, response = api.post(
            f"/internal/accounts/{account_key}/{action}",
            headers={"INTERNAL-TOKEN": internal_token},
        )

        assert status == 404
        assert response["code"] == "RNV001021"
