from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from database import Context
from models import (
    Account,
    Entry,
    Transaction,
    TransactionStatus,
    TransactionStatusEvent,
    TransactionType,
)


class LedgerRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_account_by_key(self, account_key: str) -> Account:
        return self.session.query(Account).filter(Account.account_key == account_key.lower()).first()

    def get_account_by_code(self, code: str) -> Account:
        return self.session.query(Account).filter(Account.code == code.lower()).first()

    def get_transaction_by_key(self, transaction_key: str) -> Transaction:
        return self.session.query(Transaction).filter(Transaction.transaction_key == transaction_key.lower()).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Transaction:
        return self.session.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()

    def lock_account(self, account_id: int) -> None:
        self.session.query(Account.id).filter(Account.id == account_id).with_for_update().one()

    def balance_of(self, account_id: int) -> int:
        credit = func.coalesce(func.sum(Entry.credit_minor), 0)
        debit = func.coalesce(func.sum(Entry.debit_minor), 0)
        return self.session.query(credit - debit).filter(Entry.account_id == account_id).scalar()

    def create(
        self,
        type_enumerator: str,
        status_enumerator: str,
        idempotency_key: str,
        payload_hash: str,
        legs: list,
        settles_transaction_id: int = None,
        reverses_transaction_id: int = None,
    ) -> Transaction:
        status = self.get_status(status_enumerator)

        transaction = Transaction()
        transaction.transaction_key = str(uuid4())
        transaction.type = self.get_type(type_enumerator)
        transaction.status = status
        transaction.idempotency_key = idempotency_key
        transaction.payload_hash = payload_hash
        transaction.settles_transaction_id = settles_transaction_id
        transaction.reverses_transaction_id = reverses_transaction_id
        self.session.add(transaction)
        self.session.flush()

        for leg in legs:
            entry = Entry()
            entry.transaction_id = transaction.id
            entry.account_id = leg["account"].id
            entry.debit_minor = leg["debit_minor"]
            entry.credit_minor = leg["credit_minor"]
            self.session.add(entry)

        event = TransactionStatusEvent()
        event.transaction_id = transaction.id
        event.status_id = status.id
        event.event_datetime = datetime.now(timezone.utc)
        self.session.add(event)

        self.session.flush()
        return transaction

    def get_type(self, enumerator: str) -> TransactionType:
        return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).one()

    def get_status(self, enumerator: str) -> TransactionStatus:
        return self.session.query(TransactionStatus).filter(TransactionStatus.enumerator == enumerator).one()

    def violated_constraint(self, error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
