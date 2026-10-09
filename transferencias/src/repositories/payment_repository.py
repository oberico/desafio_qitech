from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from database import Context
from models import Origin, Payment, PaymentStatus

IDEMPOTENCY_CONSTRAINT = "uq_payment_idempotency"


class PaymentRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def build(self, payment_data: dict, idempotency_key: str, payload_hash: str) -> Payment:
        payment = Payment()
        payment.payment_key = str(uuid4())
        payment.company_key = payment_data["company_key"].lower()
        payment.account_key = payment_data["account_key"].lower()
        payment.method = payment_data.get("method")
        payment.amount_minor = payment_data["amount_minor"]
        payment.origin = self.get_origin(payment_data["origin"])
        payment.status = self.get_status(PaymentStatus.PENDING)
        payment.idempotency_key = idempotency_key
        payment.payload_hash = payload_hash
        return payment

    def try_insert(self, payment: Payment) -> bool:
        try:
            self.session.add(payment)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            if self._violated_constraint(error) != IDEMPOTENCY_CONSTRAINT:
                raise
            return False
        return True

    def get_by_key(self, payment_key: str) -> Payment:
        return self.session.query(Payment).filter(Payment.payment_key == payment_key).first()

    def get_by_idempotency_key(self, company_key: str, idempotency_key: str) -> Payment:
        return (
            self.session.query(Payment)
            .filter(Payment.company_key == company_key.lower(), Payment.idempotency_key == idempotency_key)
            .one()
        )

    def get_origin(self, enumerator: str) -> Origin:
        return self.session.query(Origin).filter(Origin.enumerator == enumerator).one()

    def get_status(self, enumerator: str) -> PaymentStatus:
        return self.session.query(PaymentStatus).filter(PaymentStatus.enumerator == enumerator).one()

    def _violated_constraint(self, error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
