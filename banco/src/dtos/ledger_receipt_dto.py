class LedgerReceiptDTO:
    @staticmethod
    def obj_to_dict(receipt) -> dict:
        return {
            "transaction_key": receipt.transaction_key,
            "idempotency_key": receipt.idempotency_key,
            "amount_minor": int(receipt.amount_minor),
            "created_at": receipt.created_at.isoformat(),
        }
