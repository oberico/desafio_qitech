from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator
from tests.utils.request_generator import RequestGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}


@pytest.fixture
def account_with_rejected_company(bank, client_token):
    company_key = bank.create_company(client_token, RandomGenerator.cnpj_rejected_by_bureau())
    return bank.open_account(company_key, client_token)["account_key"]


@pytest.fixture
def closed_account(bank, client_token):
    company_key = bank.create_company(client_token)
    account = bank.open_account(company_key, client_token)
    bank.close_account(account["account_key"], client_token)
    return account["account_key"]


@pytest.fixture
def blocked_account(bank, client_token, internal_token):
    company_key = bank.create_company(client_token)
    account = bank.open_account(company_key, client_token)
    bank.block_account(account["account_key"], internal_token)
    return account["account_key"]


class TestPayoutAuthentication:
    def test_post_without_token_is_unauthorized(self, api):
        payload = PayloadGenerator.create_payout_payload()
        status, response = api.post("/payouts", payload, {"Idempotency-Key": str(uuid4())})
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_get_without_token_is_unauthorized(self, api):
        status, response = api.get(f"/payouts/{uuid4()}")
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_post_with_invalid_token_is_unauthorized(self, api):
        payload = PayloadGenerator.create_payout_payload()
        headers = {"Authorization": "Bearer invalid", "Idempotency-Key": str(uuid4())}
        status, response = api.post("/payouts", payload, headers)
        assert status == 401
        assert response["code"] == "RNV000003"


class TestPayoutAuthorization:
    def test_refuses_account_of_another_client(self, payouts, other_payouts, payout_payload):
        payload = payout_payload()
        status, response = other_payouts.post_payout(payload, str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001018"

    def test_refuses_nonexistent_account(self, payouts):
        status, response = payouts.post_payout(PayloadGenerator.create_payout_payload(), str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001018"
        assert set(response) == ERROR_FIELDS

    @pytest.mark.parametrize(
        "account_fixture",
        ["account_with_rejected_company", "closed_account", "blocked_account"],
        ids=["rejected", "closed", "blocked"],
    )
    def test_refuses_account_that_is_not_active(self, payouts, request, account_fixture):
        account_key = request.getfixturevalue(account_fixture)
        payload = PayloadGenerator.create_payout_payload(account_key=account_key)
        status, response = payouts.post_payout(payload, str(uuid4()))
        assert status == 403
        assert response["code"] == "RNV001031"

    def test_accepts_payout_again_after_the_account_is_unblocked(
        self, payouts, funded_account, bank, internal_token
    ):
        account_key = funded_account()
        payload = PayloadGenerator.create_payout_payload(account_key=account_key)

        bank.block_account(account_key, internal_token)
        status, response = payouts.post_payout(payload, str(uuid4()))
        assert status == 403
        assert response["code"] == "RNV001031"

        bank.unblock_account(account_key, internal_token)
        status, _ = payouts.post_payout(payload, str(uuid4()))
        assert status == 201

    def test_payout_carries_the_company_of_the_account(self, payouts, bank, client_token, funded_account):
        account_key = funded_account()
        payload = PayloadGenerator.create_payout_payload(account_key=account_key)

        status, response = payouts.post_payout(payload, str(uuid4()))

        assert status == 201
        assert response["account_key"] == account_key
        assert len(response["company_key"]) == 36
