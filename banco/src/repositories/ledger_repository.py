from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Account, AllowedTransition, Entry, Transaction, TransactionStatus, TransactionStatusEvent, TransactionType


class LedgerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_account_by_key(self, account_key: str) -> Account:
        return self.session.query(Account).filter(Account.account_key == account_key.lower()).first()

    def get_account_by_code(self, code: str) -> Account:
        return self.session.query(Account).filter(Account.code == code.lower()).first()

    def get_transaction_by_key(self, transaction_key: str) -> Transaction:
        return self.session.query(Transaction).filter(Transaction.transaction_key == transaction_key.lower()).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Transaction:
        return self.session.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()

    def lock_transaction(self, transaction_id: int) -> None:
        self.session.query(Transaction.id).filter(Transaction.id == transaction_id).with_for_update().one()

    def is_consumed(self, transaction_id: int) -> bool:
        consumer = self.session.query(Transaction.id).filter(
            or_(
                Transaction.settles_transaction_id == transaction_id,
                Transaction.reverses_transaction_id == transaction_id,
            )
        )
        return consumer.first() is not None

    def lock_account(self, account_id: int) -> None:
        self.session.query(Account.id).filter(Account.id == account_id).with_for_update().one()

    def balance_of(self, account_id: int) -> int:
        credit = func.coalesce(func.sum(Entry.credit_minor), 0)
        debit = func.coalesce(func.sum(Entry.debit_minor), 0)
        return self.session.query(credit - debit).filter(Entry.account_id == account_id).scalar()

    def list_statement(
        self, account_id: int, before_entry_id: int, created_from: datetime, created_to: datetime, limit: int
    ) -> list:
        query = (
            self.session.query(Entry, Transaction)
            .join(Transaction, Transaction.id == Entry.transaction_id)
            .filter(Entry.account_id == account_id)
        )
        if before_entry_id is not None:
            query = query.filter(Entry.id < before_entry_id)
        if created_from is not None:
            query = query.filter(Entry.created_at >= created_from)
        if created_to is not None:
            query = query.filter(Entry.created_at <= created_to)
        return query.order_by(Entry.id.desc()).limit(limit).all()

    def get_type(self, enumerator: str) -> TransactionType:
        return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).one()

    def get_status(self, enumerator: str) -> TransactionStatus:
        return self.session.query(TransactionStatus).filter(TransactionStatus.enumerator == enumerator).one()

    def is_transition_allowed(self, transaction: Transaction, to_status_enumerator: str) -> bool:
        to_status = self.get_status(to_status_enumerator)
        allowed = self.session.query(AllowedTransition.id).filter(
            AllowedTransition.type_id == transaction.type_id,
            AllowedTransition.from_status_id == transaction.status_id,
            AllowedTransition.to_status_id == to_status.id,
        )
        return allowed.first() is not None

    def change_status(self, transaction: Transaction, status_enumerator: str) -> None:
        status = self.get_status(status_enumerator)
        transaction.status = status
        self.session.add(
            TransactionStatusEvent(
                transaction_id=transaction.id,
                status_id=status.id,
                event_datetime=datetime.now(timezone.utc),
            )
        )
        self.session.flush()

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
        transaction = Transaction(
            transaction_key=str(uuid4()),
            type=self.get_type(type_enumerator),
            status=status,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            settles_transaction_id=settles_transaction_id,
            reverses_transaction_id=reverses_transaction_id,
        )
        self.session.add(transaction)
        self.session.flush()

        for leg in legs:
            self.session.add(
                Entry(
                    transaction_id=transaction.id,
                    account_id=leg["account"].id,
                    debit_minor=leg["debit_minor"],
                    credit_minor=leg["credit_minor"],
                )
            )
        self.session.add(
            TransactionStatusEvent(
                transaction_id=transaction.id,
                status_id=status.id,
                event_datetime=datetime.now(timezone.utc),
            )
        )
        self.session.flush()
        return transaction

    def violated_constraint(self, error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
