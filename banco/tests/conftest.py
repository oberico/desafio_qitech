import os

import pytest
import requests

from tests.utils.request_generator import RequestGenerator

BANCO_API_URL = os.getenv("BANCO_API_URL", "http://localhost:8001")


@pytest.fixture(scope="session")
def api_url() -> str:
    return BANCO_API_URL


@pytest.fixture(scope="session")
def api_is_up(api_url) -> None:
    try:
        requests.get(f"{api_url}/health_check", timeout=5)
    except requests.exceptions.RequestException:
        pytest.exit(f"could not reach the banco API at {api_url}; run `docker compose up` first", returncode=1)


@pytest.fixture(scope="session")
def api(api_url, api_is_up) -> RequestGenerator:
    return RequestGenerator(api_url)
