import os

import pytest
import requests

from tests.utils.client_requests import ClientRequests
from tests.utils.payload_generator import PayloadGenerator
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
