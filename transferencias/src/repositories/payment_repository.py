from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Payment, PaymentMethod, PaymentStatus


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

    def get_by_key(self, payment_key: str) -> Payment:
        return self.session.query(Payment).filter(Payment.payment_key == payment_key).first()

    def get_method(self, enumerator: str) -> PaymentMethod:
        return self.session.query(PaymentMethod).filter(PaymentMethod.enumerator == enumerator).first()

    def get_status(self, enumerator: str) -> PaymentStatus:
        return self.session.query(PaymentStatus).filter(PaymentStatus.enumerator == enumerator).first()

    @staticmethod
    def _violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
