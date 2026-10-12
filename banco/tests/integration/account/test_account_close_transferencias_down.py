import os

import pytest

from tests.utils.account_requests import AccountRequests
from tests.utils.request_generator import RequestGenerator

BANCO_FAULT_API_URL = os.getenv("BANCO_FAULT_API_URL", "http://localhost:8011")

pytestmark = pytest.mark.fault


@pytest.fixture(scope="module")
def fault_accounts() -> AccountRequests:
    fault_api = RequestGenerator(BANCO_FAULT_API_URL)
    try:
        fault_api.get("/health_check")
    except Exception:
        pytest.exit(
            f"could not reach the banco fault API at {BANCO_FAULT_API_URL}; run `docker compose --profile fault up -d` first",
            returncode=1,
        )
    return AccountRequests(fault_api)


class TestAccountCloseTransferenciasDown:
    def test_refuses_closing_when_transferencias_is_unreachable(self, fault_accounts, active_account, client_token):
        status, response = fault_accounts.close(active_account, client_token)
        assert status == 503
        assert response["code"] == "RNV001036"

    def test_account_stays_active_when_transferencias_is_unreachable(
        self, fault_accounts, accounts, active_account, client_token
    ):
        status, _ = fault_accounts.close(active_account, client_token)
        assert status == 503

        status, response = accounts.get_account(active_account, client_token)
        assert status == 200
        assert response["status"] == "active"
