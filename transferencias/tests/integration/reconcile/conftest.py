import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.payout_requests import PayoutRequests
from tests.utils.random_generator import RandomGenerator
from tests.utils.reconcile_requests import ReconcileRequests

BACKOFF_BASE_SECONDS = int(os.getenv("PAYOUT_BACKOFF_BASE_SECONDS", "60"))
MAX_ATTEMPTS = int(os.getenv("PAYOUT_MAX_ATTEMPTS", "3"))
MAX_PER_RUN = int(os.getenv("PAYOUT_MAX_PER_RUN", "50"))
DEFAULT_FUNDING_MINOR = 5_000_000
DEFAULT_AMOUNT_MINOR = 1_000


@pytest.fixture(scope="session")
def payouts(api, client_token) -> PayoutRequests:
    return PayoutRequests(api, client_token)


@pytest.fixture(scope="session")
def reconcile(api_url, internal_token) -> ReconcileRequests:
    return ReconcileRequests(api_url, internal_token)


@pytest.fixture(scope="session")
def open_account(bank, internal_token, client_token):
    def _open(funding_minor: int = DEFAULT_FUNDING_MINOR) -> str:
        company_key = bank.create_company(client_token)
        account = bank.open_account(company_key, client_token)
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


@pytest.fixture(scope="session")
def new_payout(open_account, payouts):
    def _create(scenario: str = None, amount_minor: int = DEFAULT_AMOUNT_MINOR, account_key: str = None) -> dict:
        destination = {"bank_code": "341", "agency": "0001", "account": RandomGenerator.uuid()[:8]}
        if scenario:
            destination["scenario"] = scenario
        payload = PayloadGenerator.create_payout_payload(
            account_key=account_key or open_account(),
            amount_minor=amount_minor,
            destination=destination,
        )
        status, payout = payouts.post_payout(payload, str(uuid4()))
        assert status == 201, f"could not create the payout: {status} {payout}"
        return payout

    return _create


def now() -> datetime:
    return datetime.now(timezone.utc)


def at(base: datetime, seconds: int) -> str:
    return (base + timedelta(seconds=seconds)).isoformat()


def listed_in(response: dict) -> set:
    return set(response["settled"]) | set(response["failed"]) | set(response["pending"])


def settlement_replay(bank, internal_token, payout: dict) -> tuple:
    payload = {
        "type": "settlement",
        "settles_transaction_key": payout["transaction_key"],
        "entries": [
            {"account_code": "in_transit", "debit_minor": payout["amount_minor"]},
            {"account_code": "reserves", "credit_minor": payout["amount_minor"]},
        ],
    }
    return bank.post_ledger_transaction(payload, f"settlement:{payout['payout_key']}", internal_token)


def reversal_replay(bank, internal_token, payout: dict) -> tuple:
    fee_minor = payout["fee_minor"]
    entries = []
    if fee_minor > 0:
        entries.append({"account_code": "revenue", "debit_minor": fee_minor})
    entries.append({"account_code": "in_transit", "debit_minor": payout["amount_minor"]})
    entries.append({"account_key": payout["account_key"], "credit_minor": payout["amount_minor"] + fee_minor})
    payload = {"type": "reversal", "reverses_transaction_key": payout["transaction_key"], "entries": entries}
    return bank.post_ledger_transaction(payload, f"reversal:{payout['payout_key']}", internal_token)
