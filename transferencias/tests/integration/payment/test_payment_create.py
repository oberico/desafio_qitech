from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator


class TestPaymentCreate:
    def test_creates_payment_held_with_snapshot(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=10000, method="pix")
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["status"] == "held"
        assert response["amount_minor"] == 10000
        assert response["method"] == "pix"
        assert response["fee_bps"] == 99
        assert response["transaction_key"] is None
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=23, minutes=59) <= release_at <= before + timedelta(hours=24, minutes=1)

    def test_boleto_snapshots_its_own_fee_and_window(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="boleto")
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == 199
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=71, minutes=59) <= release_at <= before + timedelta(hours=72, minutes=1)

    def test_card_snapshots_its_own_fee_and_window(self, payments):
        payload = PayloadGenerator.create_payment_payload(method="card")
        before = datetime.now(timezone.utc)

        status, response = payments.post_payment(payload, str(uuid4()))

        assert status == 201
        assert response["fee_bps"] == 499
        release_at = datetime.fromisoformat(response["release_at"])
        assert before + timedelta(hours=719, minutes=59) <= release_at <= before + timedelta(hours=720, minutes=1)

    def test_amount_above_float_precision_is_stored_exactly(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=9_007_199_254_740_993)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 201
        assert response["amount_minor"] == 9_007_199_254_740_993
        assert isinstance(response["amount_minor"], int)

    def test_amount_is_returned_as_an_integer(self, payments):
        payload = PayloadGenerator.create_payment_payload(amount_minor=11000)
        status, response = payments.post_payment(payload, str(uuid4()))
        assert status == 201
        assert isinstance(response["amount_minor"], int)
