from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

METHOD_SNAPSHOTS = {
    "pix": ("pix", 99, 24),
    "boleto": ("boleto", 199, 72),
    "card": ("card", 499, 720),
}


class TestPaymentCreate:
    def test_creates_payment_held(self, payments, payment_payload):
        payload = payment_payload(amount_minor=10000, method="pix")

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["status"] == "held"
        assert response["amount_minor"] == 10000
        assert isinstance(response["amount_minor"], int)
        assert response["method"] == "pix"
        assert response["transaction_key"] is not None

    @pytest.mark.parametrize("method, fee_bps, window_hours", METHOD_SNAPSHOTS.values(), ids=METHOD_SNAPSHOTS.keys())
    def test_snapshots_the_method_fee_and_window(self, payments, payment_payload, method, fee_bps, window_hours):
        payload = payment_payload(method=method)
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == fee_bps
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=window_hours - 1, minutes=59) <= release_at <= before + timedelta(hours=window_hours, minutes=1)

    def test_amount_above_float_precision_is_stored_exactly(self, payments, payment_payload):
        payload = payment_payload(amount_minor=9_007_199_254_740_993)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 201
        assert response["amount_minor"] == 9_007_199_254_740_993
        assert isinstance(response["amount_minor"], int)
