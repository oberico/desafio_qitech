class TestAccountUnblock:
    def test_unblocks_blocked_account(self, accounts, blocked_account, internal_token):
        status, response = accounts.unblock(blocked_account, internal_token)

        assert status == 200
        assert response["account_key"] == blocked_account
        assert response["status"] == "active"

    def test_unblocked_account_is_active_when_read_again(self, accounts, blocked_account, internal_token, client_token):
        status, _ = accounts.unblock(blocked_account, internal_token)
        assert status == 200

        status, response = accounts.get_account(blocked_account, client_token)

        assert status == 200
        assert response["status"] == "active"
