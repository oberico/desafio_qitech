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
    "empty_body": (lambda: {}, "RNV000007"),
    "missing_account_key": (lambda: payload_without("account_key"), "RNV000007"),
    "missing_purpose": (lambda: payload_without("purpose"), "RNV000007"),
    "missing_amount": (lambda: payload_without("amount_minor"), "RNV000007"),
    "missing_destination": (lambda: payload_without("destination"), "RNV000007"),
    "unknown_purpose": (lambda: PayloadGenerator.create_payout_payload(purpose="gift"), "RNV000009"),
    "uppercase_purpose": (lambda: PayloadGenerator.create_payout_payload(purpose="WITHDRAWAL"), "RNV000009"),
    "unknown_field": (lambda: PayloadGenerator.create_payout_payload(unexpected=1), "RNV000008"),
    "company_key_in_body": (lambda: PayloadGenerator.create_payout_payload(company_key=RandomGenerator.uuid()), "RNV000008"),
    "scenario_outside_destination": (lambda: PayloadGenerator.create_payout_payload(scenario="confirm"), "RNV000008"),
    "malformed_account_key": (lambda: PayloadGenerator.create_payout_payload(account_key="x" * 36), "RNV000009"),
    "amount_as_string": (lambda: PayloadGenerator.create_payout_payload(amount_minor="1000"), "RNV000009"),
    "fractional_amount": (lambda: PayloadGenerator.create_payout_payload(amount_minor=110.5), "RNV000009"),
    "float_typed_whole_amount": (lambda: PayloadGenerator.create_payout_payload(amount_minor=110.0), "RNV000009"),
    "boolean_amount": (lambda: PayloadGenerator.create_payout_payload(amount_minor=True), "RNV000009"),
    "empty_destination": (lambda: PayloadGenerator.create_payout_payload(destination={}), "RNV000010"),
    "destination_as_string": (lambda: PayloadGenerator.create_payout_payload(destination="341"), "RNV000009"),
    "destination_as_list": (lambda: PayloadGenerator.create_payout_payload(destination=[{"a": 1}]), "RNV000009"),
    "destination_null": (lambda: PayloadGenerator.create_payout_payload(destination=None), "RNV000009"),
    "unknown_scenario": (lambda: PayloadGenerator.create_payout_payload(destination={"scenario": "explode"}), "RNV000009"),
    "oversized_destination": (lambda: PayloadGenerator.create_payout_payload(destination={"note": "x" * 5000}), "RNV000010"),
}


class TestPayoutValidation:
    @pytest.mark.parametrize("build_payload, code", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_refuses_invalid_body(self, payouts, build_payload, code):
        status, response = payouts.post_payout(build_payload(), str(uuid4()))
        assert status == 400
        assert response["code"] == code

    def test_refuses_missing_idempotency_key(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(), None)
        assert status == 400
        assert response["code"] == "RNV000012"

    def test_refuses_idempotency_key_above_fifty_characters(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(), "k" * 51)
        assert status == 400
        assert response["code"] == "RNV000012"


    def test_idempotency_key_translation_states_the_accepted_size(self, payouts, payout_payload):
        _, response = payouts.post_payout(payout_payload(), None)
        assert response["translation"] == "O header Idempotency-Key é obrigatório e deve ter de 1 a 50 caracteres."

    def test_enum_translation_lists_the_accepted_values(self, payouts):
        _, response = payouts.post_payout(PayloadGenerator.create_payout_payload(purpose="gift"), str(uuid4()))
        assert response["translation"] == (
            "O campo purpose tem tipo ou formato inválido: esperado um destes valores: withdrawal, bill_payment, transfer."
        )

    def test_oversized_destination_translation_states_the_limit(self, payouts):
        payload = PayloadGenerator.create_payout_payload(destination={"note": "x" * 5000})
        _, response = payouts.post_payout(payload, str(uuid4()))
        assert response["translation"] == "O campo destination está fora do limite: deve ter no máximo 4096 bytes."

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

    def test_amount_whose_total_with_the_fee_is_above_bigint_is_refused(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(amount_minor=BIGINT_MAX), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"

    def test_total_below_bigint_passes_validation_and_meets_the_ledger(self, payouts, payout_payload):
        status, response = payouts.post_payout(payout_payload(amount_minor=BIGINT_MAX // 2), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001006"
