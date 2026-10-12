from uuid import uuid4

import pytest

BIGINT_MAX = 9223372036854775807


class TestPaymentAmountLimits:
    @pytest.mark.parametrize("amount", [BIGINT_MAX + 1, 10**30])
    def test_refuses_amount_above_bigint(self, payments, payment_payload, amount):
        status, response = payments.post_payment(payment_payload(amount_minor=amount), str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001023"
        assert response["translation"] == f"O valor passa do máximo permitido de {BIGINT_MAX} centavos."

    def test_accepts_exact_bigint_limit(self, payments, payment_payload):
        status, response = payments.post_payment(payment_payload(amount_minor=BIGINT_MAX), str(uuid4()))
        assert status == 201
        assert response["amount_minor"] == BIGINT_MAX
