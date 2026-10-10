import os

import pytest
import requests

from tests.utils.request_generator import RequestGenerator
from tests.utils.payment_requests import PaymentRequests

TRANSFERENCIAS_API_URL = os.getenv("TRANSFERENCIAS_API_URL", "http://localhost:8002")


@pytest.fixture(scope="session")
def api_url() -> str:
    return TRANSFERENCIAS_API_URL


@pytest.fixture(scope="session")
def api_is_up(api_url) -> None:
    try:
        requests.get(f"{api_url}/health_check", timeout=5)
    except requests.exceptions.RequestException:
        pytest.exit(f"could not reach the transferencias API at {api_url}; run `docker compose up -d` first", returncode=1)


@pytest.fixture(scope="session")
def api(api_url, api_is_up) -> RequestGenerator:
    return RequestGenerator(api_url)


@pytest.fixture(scope="session")
def payments(api) -> PaymentRequests:
    return PaymentRequests(api)
