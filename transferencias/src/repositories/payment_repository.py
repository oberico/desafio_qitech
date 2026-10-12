from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Payment, PaymentMethod, PaymentStatus, PaymentStatusEvent


IDEMPOTENCY_CONSTRAINT = "uq_payment_idempotency"


class PaymentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def try_create(self, payment: Payment) -> bool:
        try:
            self.session.add(payment)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            if self._violated_constraint(error) != IDEMPOTENCY_CONSTRAINT:
                raise
            return False
        return True

    def get_by_idempotency_key(self, company_key: str, idempotency_key: str) -> Payment:
        return (
            self.session.query(Payment)
            .filter(Payment.company_key == company_key, Payment.idempotency_key == idempotency_key)
            .first()
        )

    def get_by_key(self, payment_key: str, client_key: str) -> Payment:
        return (
            self.session.query(Payment)
            .filter(Payment.payment_key == payment_key, Payment.client_key == client_key)
            .first()
        )

    def list_newest_first(self, client_key: str, limit: int, before_id: int = None, status: str = None) -> list:
        query = self.session.query(Payment).filter(Payment.client_key == client_key)
        if status is not None:
            query = query.join(PaymentStatus, PaymentStatus.id == Payment.status_id).filter(
                PaymentStatus.enumerator == status
            )
        if before_id is not None:
            query = query.filter(Payment.id < before_id)
        return query.order_by(Payment.id.desc()).limit(limit).all()

    def list_all_newest_first(
        self, limit: int, before_id: int = None, status: str = None, company_key: str = None
    ) -> list:
        query = self.session.query(Payment)
        if company_key is not None:
            query = query.filter(Payment.company_key == company_key)
        if status is not None:
            query = query.join(PaymentStatus, PaymentStatus.id == Payment.status_id).filter(
                PaymentStatus.enumerator == status
            )
        if before_id is not None:
            query = query.filter(Payment.id < before_id)
        return query.order_by(Payment.id.desc()).limit(limit).all()

    def get_locked_by_key(self, payment_key: str, client_key: str) -> Payment:
        return (
            self.session.query(Payment)
            .filter(Payment.payment_key == payment_key, Payment.client_key == client_key)
            .with_for_update()
            .populate_existing()
            .first()
        )

    def list_due_ids(self, status_id: int, as_of: datetime) -> list:
        rows = (
            self.session.query(Payment.id)
            .filter(Payment.status_id == status_id, Payment.release_at <= as_of)
            .order_by(Payment.id)
            .all()
        )
        return [row.id for row in rows]

    def get_locked_by_id(self, payment_id: int) -> Payment:
        return (
            self.session.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .populate_existing()
            .first()
        )

    def count_by_account_and_status(self, account_key: str, status_id: int) -> int:
        return (
            self.session.query(func.count(Payment.id))
            .filter(Payment.account_key == account_key, Payment.status_id == status_id)
            .scalar()
        )

    def existing_transaction_keys(self, transaction_keys: list) -> set:
        if not transaction_keys:
            return set()
        rows = self.session.query(Payment.transaction_key).filter(Payment.transaction_key.in_(transaction_keys)).all()
        return {row.transaction_key for row in rows}

    def add_status_event(self, event: PaymentStatusEvent) -> None:
        self.session.add(event)
        self.session.flush()

    def get_method(self, enumerator: str) -> PaymentMethod:
        return (
            self.session.query(PaymentMethod)
            .filter(PaymentMethod.enumerator == enumerator)
            .order_by(PaymentMethod.version.desc())
            .first()
        )

    def get_status(self, enumerator: str) -> PaymentStatus:
        return self.session.query(PaymentStatus).filter(PaymentStatus.enumerator == enumerator).first()

    @staticmethod
    def _violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
