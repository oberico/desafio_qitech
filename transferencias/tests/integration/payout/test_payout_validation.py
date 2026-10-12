from uuid import uuid4

import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}
BIGINT_MAX = 9223372036854775807


def payload_without(field: str) -> dict:
    payload = PayloadGenerator.create_payout_payload()
    del payload[field]
    return payload


INVALID_BODIES = {
    "empty_body": lambda: {},
    "missing_account_key": lambda: payload_without("account_key"),
    "missing_purpose": lambda: payload_without("purpose"),
    "missing_amount": lambda: payload_without("amount_minor"),
    "missing_destination": lambda: payload_without("destination"),
    "unknown_purpose": lambda: PayloadGenerator.create_payout_payload(purpose="gift"),
    "uppercase_purpose": lambda: PayloadGenerator.create_payout_payload(purpose="WITHDRAWAL"),
    "unknown_field": lambda: PayloadGenerator.create_payout_payload(unexpected=1),
    "company_key_in_body": lambda: PayloadGenerator.create_payout_payload(company_key=RandomGenerator.uuid()),
    "scenario_outside_destination": lambda: PayloadGenerator.create_payout_payload(scenario="confirm"),
    "malformed_account_key": lambda: PayloadGenerator.create_payout_payload(account_key="x" * 36),
    "amount_as_string": lambda: PayloadGenerator.create_payout_payload(amount_minor="1000"),
    "fractional_amount": lambda: PayloadGenerator.create_payout_payload(amount_minor=110.5),
    "float_typed_whole_amount": lambda: PayloadGenerator.create_payout_payload(amount_minor=110.0),
    "boolean_amount": lambda: PayloadGenerator.create_payout_payload(amount_minor=True),
    "empty_destination": lambda: PayloadGenerator.create_payout_payload(destination={}),
    "destination_as_string": lambda: PayloadGenerator.create_payout_payload(destination="341"),
    "destination_as_list": lambda: PayloadGenerator.create_payout_payload(destination=[{"a": 1}]),
    "destination_null": lambda: PayloadGenerator.create_payout_payload(destination=None),
    "unknown_scenario": lambda: PayloadGenerator.create_payout_payload(destination={"scenario": "explode"}),
    "oversized_destination": lambda: PayloadGenerator.create_payout_payload(destination={"note": "x" * 5000}),
}


class TestPayoutValidation:
    @pytest.mark.parametrize("build_payload", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_refuses_invalid_body(self, payouts, build_payload):
        status, response = payouts.post_payout(build_payload(), str(uuid4()))
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_missing_idempotency_key(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(), None)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_refuses_idempotency_key_above_fifty_characters(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(), "k" * 51)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_accepts_destination_at_the_size_limit(self, payouts, payout_payload):
        destination = {"note": "x" * 4000}
        status, _ = payouts.post_payout(payout_payload(destination=destination), str(uuid4()))
        assert status == 201

    def test_schema_error_describes_the_offending_field(self, payouts):
        status, response = payouts.post_payout(PayloadGenerator.create_payout_payload(purpose="gift"), str(uuid4()))
        assert status == 400
        assert "purpose" in response["description"]
        assert set(response) == ERROR_FIELDS
        assert all(response[field] for field in ERROR_FIELDS)

    @pytest.mark.parametrize("amount", [0, -1])
    def test_refuses_non_positive_amount(self, payouts, payout_payload, amount):
        status, response = payouts.post_payout(payout_payload(amount_minor=amount), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"
        assert set(response) == ERROR_FIELDS

    @pytest.mark.parametrize("amount", [BIGINT_MAX + 1, 10**30])
    def test_refuses_amount_above_bigint(self, payouts, payout_payload, amount):
        status, response = payouts.post_payout(payout_payload(amount_minor=amount), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"

    def test_amount_at_bigint_limit_passes_validation_and_meets_the_ledger(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(amount_minor=BIGINT_MAX), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001006"
