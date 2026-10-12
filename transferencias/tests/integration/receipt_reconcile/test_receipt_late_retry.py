from tests.integration.receipt_reconcile.conftest import after_the_grace


class TestReceiptLateRetry:
    def test_retry_inside_the_grace_recovers_the_receipt(self, receipt_reconcile, orphan_receipt, payments):
        orphan = orphan_receipt()

        status, payment = payments.post_payment(orphan["payload"], orphan["idempotency_key"])
        assert status == 201
        assert payment["transaction_key"] == orphan["transaction_key"]

        status, response = receipt_reconcile.run(after_the_grace())
        assert status == 200
        assert orphan["transaction_key"] not in response["refunded"]

    def test_retry_after_the_refund_is_refused(self, receipt_reconcile, orphan_receipt, payments):
        orphan = orphan_receipt()
        status, response = receipt_reconcile.run(after_the_grace())
        assert orphan["transaction_key"] in response["refunded"]

        status, response = payments.post_payment(orphan["payload"], orphan["idempotency_key"])

        assert status == 409
        assert response["code"] == "RNV001038"
        assert response["translation"] == (
            "O recebimento desta Idempotency-Key já foi estornado pela reconciliação; a venda expirou. "
            "Use uma nova Idempotency-Key."
        )

    def test_refused_retry_creates_no_payment(self, receipt_reconcile, orphan_receipt, payments):
        orphan = orphan_receipt()
        receipt_reconcile.run(after_the_grace())

        payments.post_payment(orphan["payload"], orphan["idempotency_key"])
        status, response = payments.post_payment(orphan["payload"], orphan["idempotency_key"])

        assert status == 409
        assert response["code"] == "RNV001038"
