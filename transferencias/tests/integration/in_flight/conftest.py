from uuid import uuid4

import pytest

from tests.integration.payout.conftest import funded_account, other_payouts, payout_payload, payouts
from tests.utils.in_flight_requests import InFlightRequests


@pytest.fixture(scope="session")
def in_flight(api, internal_token) -> InFlightRequests:
    return InFlightRequests(api, internal_token)


@pytest.fixture
def held_payment_account(payments, payment_payload):
    def _create() -> str:
        status, response = payments.post_payment(payment_payload(), str(uuid4()))
        assert status == 201, f"could not create the payment of the scenario: {status} {response}"
        return response["account_key"], response["payment_key"]

    return _create
