import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.utils.payment_requests import PaymentRequests
from tests.utils.request_generator import RequestGenerator

TRANSFERENCIAS_FAULT_API_URL = os.getenv("TRANSFERENCIAS_FAULT_API_URL", "http://localhost:8012")
CONCURRENT_REQUESTS = 100

pytestmark = pytest.mark.fault


@pytest.fixture(scope="module")
def tiny_pool_payments(bank, client_token) -> PaymentRequests:
    fault_api = RequestGenerator(TRANSFERENCIAS_FAULT_API_URL)
    try:
        fault_api.get("/health_check")
    except Exception:
        pytest.exit(
            f"could not reach the fault API at {TRANSFERENCIAS_FAULT_API_URL}; run `docker compose --profile fault up -d` first",
            returncode=1,
        )
    return PaymentRequests(fault_api, client_token)


class TestPaymentServiceBusy:
    def test_exhausted_connection_pool_returns_service_unavailable(self, tiny_pool_payments):
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as pool:
            results = list(pool.map(lambda _: tiny_pool_payments.get_payment(str(uuid.uuid4())), range(CONCURRENT_REQUESTS)))

        statuses = {status for status, _ in results}
        assert statuses <= {404, 503}
        assert 503 in statuses

    def test_service_busy_response_has_the_standard_error_code(self, tiny_pool_payments):
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as pool:
            results = list(pool.map(lambda _: tiny_pool_payments.get_payment(str(uuid.uuid4())), range(CONCURRENT_REQUESTS)))

        busy = [response for status, response in results if status == 503]
        assert busy
        assert {response["code"] for response in busy} == {"RNV000006"}
