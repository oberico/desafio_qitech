from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.payout_requests import PayoutRequests

FUNDING_MINOR = 5_000_000


@pytest.fixture(scope="session")
def payouts(api, client_token) -> PayoutRequests:
    return PayoutRequests(api, client_token)


@pytest.fixture(scope="session")
def other_payouts(api, bank) -> PayoutRequests:
    return PayoutRequests(api, bank.create_client_token())


@pytest.fixture
def funded_account(bank, internal_token, client_token):
    def _open(funding_minor: int = FUNDING_MINOR, token: str = None) -> str:
        owner_token = token or client_token
        company_key = bank.create_company(owner_token)
        account = bank.open_account(company_key, owner_token)
        if funding_minor > 0:
            funding = {
                "type": "receipt",
                "entries": [
                    {"account_code": "reserves", "debit_minor": funding_minor},
                    {"account_key": account["account_key"], "credit_minor": funding_minor},
                ],
            }
            status, response = bank.post_ledger_transaction(funding, str(uuid4()), internal_token)
            assert status == 201, f"could not fund the account: {status} {response}"
        return account["account_key"]

    return _open


@pytest.fixture
def payout_payload(funded_account):
    def _build(token: str = None, funding_minor: int = FUNDING_MINOR, **overrides) -> dict:
        account_key = funded_account(funding_minor, token)
        return PayloadGenerator.create_payout_payload(account_key=account_key, **overrides)

    return _build


def payout_ledger_payload(payout: dict) -> dict:
    fee_minor = payout["fee_minor"]
    entries = [
        {"account_key": payout["account_key"], "debit_minor": payout["amount_minor"] + fee_minor},
        {"account_code": "in_transit", "credit_minor": payout["amount_minor"]},
    ]
    if fee_minor > 0:
        entries.append({"account_code": "revenue", "credit_minor": fee_minor})
    return {"type": "payout", "entries": entries}
