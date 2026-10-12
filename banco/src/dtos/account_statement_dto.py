from models import Entry, Transaction


class AccountStatementDTO:
    @staticmethod
    def obj_to_dict(rows: list, limit: int, cursor: str) -> dict:
        return {
            "data": [AccountStatementDTO._entry_to_dict(entry, transaction) for entry, transaction in rows],
            "limit": limit,
            "cursor": cursor,
            "is_last_page": cursor is None,
        }

    @staticmethod
    def _entry_to_dict(entry: Entry, transaction: Transaction) -> dict:
        return {
            "transaction_key": transaction.transaction_key,
            "type": transaction.type.enumerator,
            "debit_minor": entry.debit_minor,
            "credit_minor": entry.credit_minor,
            "created_at": entry.created_at.isoformat(),
        }
