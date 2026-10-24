import os

import pytest
import requests

from tests.utils.admin_requests import AdminRequests
from tests.utils.bank_requests import BankRequests
from tests.utils.payout_fee import SEEDED_FEE_BPS
from tests.utils.payout_fee_requests import PayoutFeeRequests
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.payment_requests import PaymentRequests
from tests.utils.request_generator import RequestGenerator

TRANSFERENCIAS_API_URL = os.getenv("TRANSFERENCIAS_API_URL", "http://localhost:8002")
BANCO_API_URL = os.getenv("BANCO_API_URL", "http://localhost:8001")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "internal-token-dev")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin-token-dev")


def exit_unless_up(name: str, url: str) -> None:
    try:
        requests.get(f"{url}/health_check", timeout=5)
    except requests.exceptions.RequestException:
        pytest.exit(f"could not reach the {name} API at {url}; run `docker compose up -d` first", returncode=1)


@pytest.fixture(scope="session")
def api_url() -> str:
    return TRANSFERENCIAS_API_URL


@pytest.fixture(scope="session")
def api_is_up(api_url) -> None:
    exit_unless_up("transferencias", api_url)


@pytest.fixture(scope="session")
def api(api_url, api_is_up) -> RequestGenerator:
    return RequestGenerator(api_url)


@pytest.fixture(scope="session")
def internal_token() -> str:
    return INTERNAL_TOKEN


@pytest.fixture(scope="session")
def admin_token() -> str:
    return ADMIN_TOKEN


@pytest.fixture(scope="session")
def admin(api) -> AdminRequests:
    return AdminRequests(api)


@pytest.fixture(scope="session")
def bank(api_is_up) -> BankRequests:
    exit_unless_up("banco", BANCO_API_URL)
    return BankRequests(RequestGenerator(BANCO_API_URL))


@pytest.fixture(scope="session")
def client_token(bank) -> str:
    return bank.create_client_token()


@pytest.fixture(scope="session")
def payments(api, client_token) -> PaymentRequests:
    return PaymentRequests(api, client_token)


@pytest.fixture(scope="session")
def other_payments(api, bank) -> PaymentRequests:
    return PaymentRequests(api, bank.create_client_token())


@pytest.fixture
def payment_payload(bank, client_token):
    def _build(token: str = None, **overrides) -> dict:
        owner_token = token or client_token
        company_key = bank.create_company(owner_token)
        bank.open_account(company_key, owner_token)
        return PayloadGenerator.create_payment_payload(company_key=company_key, **overrides)

    return _build


@pytest.fixture(scope="session")
def payout_fees(api, internal_token) -> PayoutFeeRequests:
    return PayoutFeeRequests(api, internal_token)


@pytest.fixture
def changed_payout_fee(payout_fees):
    touched = []

    def _change(fee_bps: int) -> tuple:
        touched.append(fee_bps)
        status, response = payout_fees.put(fee_bps)
        assert status in (200, 201), f"could not change the payout fee: {status} {response}"
        return status, response

    try:
        yield _change
    finally:
        if touched:
            payout_fees.put(SEEDED_FEE_BPS)
