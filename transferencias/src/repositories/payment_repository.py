from datetime import datetime

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
