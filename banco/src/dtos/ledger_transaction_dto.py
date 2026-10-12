from models import Transaction


class LedgerTransactionDTO:
    @staticmethod
    def obj_to_dict(transaction: Transaction, is_reversed: bool = False) -> dict:
        return {
            "transaction_key": transaction.transaction_key,
            "type": transaction.type.enumerator,
            "status": transaction.status.enumerator,
            "reversed": is_reversed,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
        }
