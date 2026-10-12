from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tests.integration.settlement.conftest import due_instant, settlement_ledger_payload

AMOUNT_MINOR = 100000
TOLERANCE = timedelta(minutes=2)


def create_payment(payments, payment_payload, method: str = "pix") -> dict:
    status, payment = payments.post_payment(
        payment_payload(method=method, amount_minor=AMOUNT_MINOR), str(uuid4())
    )
    assert status == 201, f"could not create the payment: {status} {payment}"
    return payment


class TestPaymentUsesTheCurrentVersion:
    def test_new_payment_uses_the_new_fee(self, changed_method, payments, payment_payload):
        changed_method("pix", 777, 5)
        payment = create_payment(payments, payment_payload)
        assert payment["fee_bps"] == 777

    def test_new_payment_uses_the_new_window(self, changed_method, payments, payment_payload):
        changed_method("pix", 777, 5)
        payment = create_payment(payments, payment_payload)
        expected = datetime.now(timezone.utc) + timedelta(hours=5)
        assert abs(datetime.fromisoformat(payment["release_at"]) - expected) < TOLERANCE

    def test_changing_one_method_does_not_affect_another(self, changed_method, payments, payment_payload):
        changed_method("pix", 777, 5)
        payment = create_payment(payments, payment_payload, "boleto")
        assert payment["fee_bps"] == 199


class TestSnapshotIsKept:
    def test_settlement_charges_the_old_fee_after_the_fee_changed(
        self, changed_method, payments, payment_payload, settlements, bank, internal_token
    ):
        payment = create_payment(payments, payment_payload)
        assert payment["fee_bps"] == 99
        changed_method("pix", 500, 24)

        settlements.run(due_instant(payment))

        old = settlement_ledger_payload(payment, 99010, 990)
        status, _ = bank.post_ledger_transaction(old, f"settlement:{payment['payment_key']}", internal_token)
        assert status == 200
        new = settlement_ledger_payload(payment, 95000, 5000)
        status, response = bank.post_ledger_transaction(new, f"settlement:{payment['payment_key']}", internal_token)
        assert status == 422
        assert response["code"] == "RNV001024"

    def test_changing_the_window_does_not_move_an_existing_release_at(
        self, changed_method, payments, payment_payload
    ):
        payment = create_payment(payments, payment_payload)
        _, before = payments.get_payment(payment["payment_key"])

        changed_method("pix", 99, 3)

        _, after = payments.get_payment(payment["payment_key"])
        assert after["release_at"] == before["release_at"]
        assert after == before
