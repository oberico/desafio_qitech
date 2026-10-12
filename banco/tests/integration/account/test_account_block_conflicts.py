from tests.utils.random_generator import RandomGenerator

class TestAccountBlockConflicts:
    def test_refuses_blocking_an_already_blocked_account(
        self, accounts, blocked_account, internal_token, client_token
    ):
        status, response = accounts.block(blocked_account, internal_token)

        assert status == 409
        assert response["code"] == "RNV001009"
        assert response["translation"] == "A conta está bloqueada, por isso esta operação não é permitida."

        status, response = accounts.get_account(blocked_account, client_token)
        assert response["status"] == "blocked"

    def test_refuses_blocking_a_closed_account(self, accounts, active_account, client_token, internal_token):
        status, _ = accounts.close(active_account, client_token)
        assert status == 200

        status, response = accounts.block(active_account, internal_token)

        assert status == 409
        assert response["code"] == "RNV001009"
        assert response["translation"] == "A conta está encerrada, por isso esta operação não é permitida."

        status, response = accounts.get_account(active_account, client_token)
        assert response["status"] == "closed"

    def test_refuses_blocking_a_rejected_account(self, accounts, open_account, client_token, internal_token):
        account_key = open_account(client_token, RandomGenerator.cnpj_rejected_by_bureau())

        status, response = accounts.block(account_key, internal_token)

        assert status == 409
        assert response["code"] == "RNV001009"
        assert response["translation"] == "A conta está reprovada, por isso esta operação não é permitida."

        status, response = accounts.get_account(account_key, client_token)
        assert response["status"] == "rejected"

    def test_refuses_unblocking_an_active_account(self, accounts, active_account, internal_token, client_token):
        status, response = accounts.unblock(active_account, internal_token)

        assert status == 409
        assert response["code"] == "RNV001010"

        status, response = accounts.get_account(active_account, client_token)
        assert response["status"] == "active"

    def test_refuses_unblocking_a_closed_account(self, accounts, active_account, client_token, internal_token):
        status, _ = accounts.close(active_account, client_token)
        assert status == 200

        status, response = accounts.unblock(active_account, internal_token)

        assert status == 409
        assert response["code"] == "RNV001010"

        status, response = accounts.get_account(active_account, client_token)
        assert response["status"] == "closed"

    def test_refuses_unblocking_a_rejected_account(self, accounts, open_account, client_token, internal_token):
        account_key = open_account(client_token, RandomGenerator.cnpj_rejected_by_bureau())

        status, response = accounts.unblock(account_key, internal_token)

        assert status == 409
        assert response["code"] == "RNV001010"

        status, response = accounts.get_account(account_key, client_token)
        assert response["status"] == "rejected"

    