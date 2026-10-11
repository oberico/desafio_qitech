from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


@pytest.fixture
def company_without_account(bank, client_token):
    return bank.create_company(client_token)


@pytest.fixture
def company_with_rejected_account(bank, client_token):
    company_key = bank.create_company(client_token, RandomGenerator.cnpj_rejected_by_bureau())
    bank.open_account(company_key, client_token)
    return company_key


@pytest.fixture
def company_with_closed_account(bank, client_token):
    company_key = bank.create_company(client_token)
    account = bank.open_account(company_key, client_token)
    bank.close_account(account["account_key"], client_token)
    return company_key


class TestPaymentAuthorization:
    def test_refuses_company_of_another_client(self, payments, other_payments, payment_payload):
        payload = payment_payload()
        status, response = other_payments.post_payment(payload, str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001018"

    def test_refuses_nonexistent_company(self, payments):
        payload = PayloadGenerator.create_payment_payload()
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001018"

    def test_refuses_company_without_account(self, payments, company_without_account):
        payload = PayloadGenerator.create_payment_payload(company_key=company_without_account)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 403
        assert response["code"] == "RNV001030"

    @pytest.mark.parametrize(
        "company_fixture", ["company_with_rejected_account", "company_with_closed_account"], ids=["rejected", "closed"]
    )
    def test_refuses_company_whose_account_is_not_active(self, payments, request, company_fixture):
        company_key = request.getfixturevalue(company_fixture)
        payload = PayloadGenerator.create_payment_payload(company_key=company_key)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 403
        assert response["code"] == "RNV001031"

    def test_refusal_has_exactly_the_four_error_fields(self, payments, company_without_account):
        payload = PayloadGenerator.create_payment_payload(company_key=company_without_account)
        _, response = payments.post_payment(payload, str(uuid4()))
        assert set(response) == ERROR_FIELDS
        assert all(response[field] for field in ERROR_FIELDS)

    def test_payment_is_charged_to_the_account_of_the_company(self, bank, client_token, payments):
        company_key = bank.create_company(client_token)
        account = bank.open_account(company_key, client_token)
        payload = PayloadGenerator.create_payment_payload(company_key=company_key)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["account_key"] == account["account_key"]
