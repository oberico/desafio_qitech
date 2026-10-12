from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Payout, PayoutAttempt, PayoutPurpose, PayoutStatus, PayoutStatusEvent

IDEMPOTENCY_CONSTRAINT = "uq_payout_idempotency"


class PayoutRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def try_create(self, payout: Payout) -> bool:
        try:
            self.session.add(payout)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            if self._violated_constraint(error) != IDEMPOTENCY_CONSTRAINT:
                raise
            return False
        return True

    def get_by_idempotency_key(self, company_key: str, idempotency_key: str) -> Payout:
        return (
            self.session.query(Payout)
            .filter(Payout.company_key == company_key, Payout.idempotency_key == idempotency_key)
            .first()
        )

    def get_by_key(self, payout_key: str, company_keys: list) -> Payout:
        return (
            self.session.query(Payout)
            .filter(Payout.payout_key == payout_key, Payout.company_key.in_(company_keys))
            .first()
        )

    def count_attempts(self, payout_id: int) -> int:
        return self.session.query(func.count(PayoutAttempt.id)).filter(PayoutAttempt.payout_id == payout_id).scalar()

    def add_status_event(self, event: PayoutStatusEvent) -> None:
        self.session.add(event)
        self.session.flush()

    def get_purpose(self, enumerator: str) -> PayoutPurpose:
        return self.session.query(PayoutPurpose).filter(PayoutPurpose.enumerator == enumerator).first()

    def get_status(self, enumerator: str) -> PayoutStatus:
        return self.session.query(PayoutStatus).filter(PayoutStatus.enumerator == enumerator).first()

    @staticmethod
    def _violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
