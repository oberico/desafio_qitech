import pytest

from tests.utils.random_generator import RandomGenerator

FUNDING_MINOR = 10_000


@pytest.fixture
def fund_account(ledger):
    def _fund(account_key: str, amount_minor: int = FUNDING_MINOR) -> None:
        payload = {
            "type": "receipt",
            "entries": [
                {"account_code": "reserves", "debit_minor": amount_minor},
                {"account_key": account_key, "credit_minor": amount_minor},
            ],
        }
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201, f"could not fund the account: {status} {response}"

    return _fund


class TestAccountCloseGuard:
    def test_refuses_closing_an_account_with_balance(self, accounts, active_account, client_token, fund_account):
        fund_account(active_account)

        status, response = accounts.close(active_account, client_token)
        assert status == 422
        assert response["code"] == "RNV001035"

    def test_refused_close_keeps_the_account_active(self, accounts, active_account, client_token, fund_account):
        fund_account(active_account)
        accounts.close(active_account, client_token)

        status, response = accounts.get_account(active_account, client_token)
        assert status == 200
        assert response["status"] == "active"

    def test_closes_once_the_balance_is_drained(self, accounts, ledger, active_account, client_token, fund_account):
        fund_account(active_account)
        drain = {
            "type": "payout",
            "entries": [
                {"account_key": active_account, "debit_minor": FUNDING_MINOR},
                {"account_code": "in_transit", "credit_minor": FUNDING_MINOR},
            ],
        }
        status, response = ledger.post_transaction(drain, RandomGenerator.uuid())
        assert status == 201, f"could not drain the account: {status} {response}"

        status, response = accounts.close(active_account, client_token)
        assert status == 200
        assert response["status"] == "closed"

    def test_status_check_comes_before_the_balance_check(self, accounts, active_account, client_token, fund_account):
        fund_account(active_account)

        status, _ = accounts.block(active_account, "internal-token-dev")
        assert status == 200

        status, response = accounts.close(active_account, client_token)
        assert status == 409
        assert response["code"] == "RNV001009"
