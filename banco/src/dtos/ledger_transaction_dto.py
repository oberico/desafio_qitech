from models import Transaction


class LedgerTransactionDTO:
    @staticmethod
    def obj_to_dict(transaction: Transaction) -> dict:
        return {
            "transaction_key": transaction.transaction_key,
            "type": transaction.type.enumerator,
            "status": transaction.status.enumerator,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
        }
