import random

import pytest

from tests.utils.payment_method_requests import PaymentMethodRequests
from tests.utils.settlement_requests import SettlementRequests

ORIGINAL_TERMS = {"pix": (99, 24), "boleto": (199, 72), "card": (499, 720)}


@pytest.fixture(scope="session")
def payment_methods(api, internal_token) -> PaymentMethodRequests:
    return PaymentMethodRequests(api, internal_token)


@pytest.fixture(scope="session")
def settlements(api_url, internal_token) -> SettlementRequests:
    return SettlementRequests(api_url, internal_token)


@pytest.fixture
def changed_method(payment_methods):
    touched = set()

    def _change(method: str, fee_bps: int = None, release_window_hours: int = None) -> tuple:
        touched.add(method)
        fee_bps = fee_bps if fee_bps is not None else random.randint(1000, 9000)
        release_window_hours = release_window_hours if release_window_hours is not None else random.randint(1, 20)
        status, response = payment_methods.put(method, fee_bps, release_window_hours)
        assert status in (200, 201), f"could not change the method: {status} {response}"
        return status, response

    try:
        yield _change
    finally:
        for method in touched:
            fee_bps, release_window_hours = ORIGINAL_TERMS[method]
            payment_methods.put(method, fee_bps, release_window_hours)
