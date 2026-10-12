from uuid import uuid4

from tests.integration.receipt_reconcile.conftest import after_the_grace, hours_from_now, receipt_entries


def replay_receipt(bank, internal_token, orphan: dict) -> dict:
    status, receipt = bank.post_ledger_transaction(
        receipt_entries(orphan["payload"]["amount_minor"]),
        f"receipt:{orphan['payload']['company_key']}:{orphan['idempotency_key']}",
        internal_token,
    )
    assert status == 200, f"o Banco não devolveu o recebimento existente: {status} {receipt}"
    return receipt


class TestReceiptReconcile:
    def test_response_has_the_instant_and_the_lists(self, receipt_reconcile):
        status, response = receipt_reconcile.run(after_the_grace())
        assert status == 200
        assert set(response) == {"as_of", "refunded", "deferred"}

    def test_refunds_a_receipt_without_payment_after_the_grace(self, receipt_reconcile, orphan_receipt, bank, internal_token):
        orphan = orphan_receipt()

        status, response = receipt_reconcile.run(after_the_grace())

        assert status == 200
        assert orphan["transaction_key"] in response["refunded"]
        assert replay_receipt(bank, internal_token, orphan)["reversed"] is True

    def test_keeps_a_receipt_inside_the_grace(self, receipt_reconcile, orphan_receipt, bank, internal_token):
        orphan = orphan_receipt()

        status, response = receipt_reconcile.run(hours_from_now(1))

        assert status == 200
        assert orphan["transaction_key"] not in response["refunded"]
        assert replay_receipt(bank, internal_token, orphan)["reversed"] is False

    def test_keeps_the_receipt_of_a_held_payment(self, receipt_reconcile, payments, payment_payload):
        status, payment = payments.post_payment(payment_payload(), str(uuid4()))
        assert status == 201

        status, response = receipt_reconcile.run(after_the_grace())

        assert status == 200
        assert payment["transaction_key"] not in response["refunded"]
        status, refunded = payments.refund_payment(payment["payment_key"])
        assert status == 200
        assert refunded["status"] == "refunded"

    def test_ignores_a_receipt_that_did_not_come_from_a_payment(self, receipt_reconcile, bank, internal_token):
        status, receipt = bank.post_ledger_transaction(receipt_entries(500), f"manual:{uuid4()}", internal_token)
        assert status == 201

        status, response = receipt_reconcile.run(after_the_grace())

        assert status == 200
        assert receipt["transaction_key"] not in response["refunded"]

    def test_running_again_does_not_refund_twice(self, receipt_reconcile, orphan_receipt):
        orphan = orphan_receipt()
        status, first = receipt_reconcile.run(after_the_grace())
        assert orphan["transaction_key"] in first["refunded"]

        status, second = receipt_reconcile.run(after_the_grace())

        assert status == 200
        assert orphan["transaction_key"] not in second["refunded"]
        assert orphan["transaction_key"] not in second["deferred"]
