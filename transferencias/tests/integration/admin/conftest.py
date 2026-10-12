from uuid import uuid4

import pytest

from tests.integration.settlement.conftest import settlements
from tests.utils.payment_requests import PaymentRequests


@pytest.fixture
def merchant(api, bank):
    return PaymentRequests(api, bank.create_client_token())


@pytest.fixture
def other_merchant(api, bank):
    return PaymentRequests(api, bank.create_client_token())


@pytest.fixture
def create_company(bank):
    def _create(merchant: PaymentRequests) -> str:
        company_key = bank.create_company(merchant.client_token)
        bank.open_account(company_key, merchant.client_token)
        return company_key

    return _create


@pytest.fixture
def create_payments(create_company):
    def _create(merchant: PaymentRequests, count: int, company_key: str = None) -> list:
        if company_key is None:
            company_key = create_company(merchant)
        keys = []
        for _ in range(count):
            payload = {"company_key": company_key, "amount_minor": 1000, "method": "pix"}
            status, response = merchant.post_payment(payload, str(uuid4()))
            assert status == 201, f"could not create the payment: {status} {response}"
            keys.append(response["payment_key"])
        return keys

    return _create
