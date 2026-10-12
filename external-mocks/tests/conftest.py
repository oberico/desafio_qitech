import os

import pytest
import requests

from tests.utils.request_generator import RequestGenerator
from tests.utils.transfer_requests import TransferRequests

EXTERNAL_MOCKS_URL = os.getenv("EXTERNAL_MOCKS_URL", "http://localhost:8003")
SHORT_TIMEOUT_SECONDS = 2


@pytest.fixture(scope="session")
def api_url() -> str:
    return EXTERNAL_MOCKS_URL


@pytest.fixture(scope="session")
def api_is_up(api_url) -> None:
    try:
        requests.get(f"{api_url}/health_check", timeout=5)
    except requests.exceptions.RequestException:
        pytest.exit(f"could not reach the external mocks service at {api_url}; run `docker compose up -d external-mocks` first", returncode=1)


@pytest.fixture(scope="session")
def api(api_url, api_is_up) -> RequestGenerator:
    return RequestGenerator(api_url)


@pytest.fixture(scope="session")
def impatient_api(api_url, api_is_up) -> RequestGenerator:
    return RequestGenerator(api_url, timeout=SHORT_TIMEOUT_SECONDS)


@pytest.fixture(scope="session")
def transfers(api) -> TransferRequests:
    return TransferRequests(api)


@pytest.fixture(scope="session")
def impatient_transfers(impatient_api) -> TransferRequests:
    return TransferRequests(impatient_api)
