class TestInternalAccountsList:
    def test_refuses_missing_internal_token(self, api):
        status, response = api.get("/internal/internal-accounts")
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refuses_client_token_in_place_of_internal_token(self, api, client_token):
        status, response = api.get("/internal/internal-accounts", {"Authorization": f"Bearer {client_token}"})
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_lists_the_three_internal_accounts(self, internal_accounts):
        status, response = internal_accounts.list_internal_accounts()
        assert status == 200
        assert sorted(account["code"] for account in response) == ["in_transit", "reserves", "revenue"]

    def test_internal_account_has_the_expected_fields(self, internal_accounts):
        _, response = internal_accounts.list_internal_accounts()
        reserves = next(account for account in response if account["code"] == "reserves")
        assert len(reserves["account_key"]) == 36
        assert reserves["class"] == "asset"
        assert reserves["normal_balance"] == "d"
        assert reserves["status"] == "active"

    def test_internal_account_does_not_expose_internal_id(self, internal_accounts):
        _, response = internal_accounts.list_internal_accounts()
        assert all(set(account) == {"account_key", "code", "class", "normal_balance", "status"} for account in response)
