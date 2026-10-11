class TestAccountBlock:
    def test_blocks_active_account(self, accounts, active_account, internal_token):
        status, response = accounts.block(active_account, internal_token)

        assert status == 200
        assert response["account_key"] == active_account
        assert response["status"] == "blocked"

    def test_blocked_account_can_still_be_read_by_its_owner(
        self, accounts, active_account, internal_token, client_token
    ):
        status, _ = accounts.block(active_account, internal_token)
        assert status == 200

        status, response = accounts.get_account(active_account, client_token)

        assert status == 200
        assert response["status"] == "blocked"

    def test_company_shows_its_blocked_account(
        self, accounts, companies, create_company, client_token, internal_token
    ):
        company_key = create_company(client_token)
        status, created = accounts.post_account(company_key, client_token)
        assert status == 201
        status, _ = accounts.block(created["account_key"], internal_token)
        assert status == 200

        status, response = companies.get_company(company_key, client_token)

        assert status == 200
        assert response["account_status"] == "blocked"

