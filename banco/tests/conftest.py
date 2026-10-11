import os

import pytest
import requests

from tests.utils.account_requests import AccountRequests
from tests.utils.client_requests import ClientRequests
from tests.utils.company_requests import CompanyRequests
from tests.utils.internal_account_requests import InternalAccountRequests
from tests.utils.ledger_requests import LedgerRequests
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator
from tests.utils.request_generator import RequestGenerator


BANCO_API_URL = os.getenv("BANCO_API_URL", "http://localhost:8001")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "internal-token-dev")


@pytest.fixture(scope="session")
def api_url() -> str:
    return BANCO_API_URL


@pytest.fixture(scope="session")
def api_is_up(api_url) -> None:
    try:
        requests.get(f"{api_url}/health_check", timeout=5)
    except requests.exceptions.RequestException:
        pytest.exit(f"could not reach the banco API at {api_url}; run `docker compose up -d` first", returncode=1)


@pytest.fixture(scope="session")
def api(api_url, api_is_up) -> RequestGenerator:
    return RequestGenerator(api_url)


@pytest.fixture(scope="session")
def internal_token() -> str:
    return INTERNAL_TOKEN


@pytest.fixture(scope="session")
def internal_accounts(api, internal_token) -> InternalAccountRequests:
    return InternalAccountRequests(api, internal_token)


@pytest.fixture(scope="session")
def internal_account_keys(internal_accounts) -> dict:
    status, response = internal_accounts.list_internal_accounts()
    assert status == 200, f"could not list the internal accounts: {status} {response}"
    return {account["code"]: account["account_key"] for account in response}


@pytest.fixture(scope="session")
def clients(api) -> ClientRequests:
    return ClientRequests(api)


@pytest.fixture
def created_client(clients) -> tuple:
    payload = PayloadGenerator.create_client_payload()
    status, response = clients.post_client(payload)
    assert status == 201, f"não deu para criar o cliente do cenário: {status} {response}"
    return payload, response


@pytest.fixture
def client_token(clients) -> str:
    status, response = clients.post_client(PayloadGenerator.create_client_payload())
    assert status == 201, f"não deu para criar o cliente do cenário: {status} {response}"
    return response["token"]


@pytest.fixture
def other_client_token(clients) -> str:
    status, response = clients.post_client(PayloadGenerator.create_client_payload())
    assert status == 201, f"não deu para criar o cliente do cenário: {status} {response}"
    return response["token"]


@pytest.fixture(scope="session")
def companies(api) -> CompanyRequests:
    return CompanyRequests(api)

@pytest.fixture(scope="session")
def ledger(api, internal_token) -> LedgerRequests:
    return LedgerRequests(api, internal_token)

@pytest.fixture(scope="session")
def accounts(api) -> AccountRequests:
    return AccountRequests(api)


@pytest.fixture
def create_company(companies):
    def _create(token: str, cnpj: str = None) -> str:
        payload = PayloadGenerator.create_company_payload(cnpj=cnpj or RandomGenerator.cnpj())
        status, response = companies.post_company(payload, token)
        assert status == 201, f"não deu para criar a empresa do cenário: {status} {response}"
        return response["company_key"]

    return _create


@pytest.fixture
def open_account(accounts, create_company):
    def _open(token: str, cnpj: str = None) -> str:
        company_key = create_company(token, cnpj)
        status, response = accounts.post_account(company_key, token)
        assert status == 201, f"não deu para abrir a conta do cenário: {status} {response}"
        return response["account_key"]

    return _open


@pytest.fixture
def active_account(open_account, client_token) -> str:
    return open_account(client_token)

@pytest.fixture
def blocked_account(accounts, active_account, internal_token) -> str:
    status, response = accounts.block(active_account, internal_token)
    assert status == 200, f"não deu para bloquear a conta do cenário: {status} {response}"
    return active_account
