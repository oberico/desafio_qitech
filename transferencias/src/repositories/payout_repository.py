from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Payout, PayoutAttempt, PayoutPurpose, PayoutResult, PayoutStatus, PayoutStatusEvent

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

    def list_pending_snapshots(self, status_id: int) -> list:
        attempts = (
            select(func.count(PayoutAttempt.id))
            .where(PayoutAttempt.payout_id == Payout.id)
            .correlate(Payout)
            .scalar_subquery()
        )
        last_result = (
            select(PayoutResult.enumerator)
            .join(PayoutAttempt, PayoutAttempt.result_id == PayoutResult.id)
            .where(PayoutAttempt.payout_id == Payout.id)
            .order_by(PayoutAttempt.attempt_number.desc())
            .limit(1)
            .correlate(Payout)
            .scalar_subquery()
        )
        return (
            self.session.query(
                Payout.id,
                attempts.label("attempts"),
                last_result.label("last_result"),
                Payout.last_attempt_at,
            )
            .filter(Payout.status_id == status_id)
            .order_by(Payout.last_attempt_at.asc().nullsfirst(), Payout.id)
            .all()
        )

    def get_locked_by_id(self, payout_id: int) -> Payout:
        return (
            self.session.query(Payout)
            .filter(Payout.id == payout_id)
            .with_for_update()
            .populate_existing()
            .first()
        )

    def get_last_attempt_result(self, payout_id: int) -> str:
        return (
            self.session.query(PayoutResult.enumerator)
            .join(PayoutAttempt, PayoutAttempt.result_id == PayoutResult.id)
            .filter(PayoutAttempt.payout_id == payout_id)
            .order_by(PayoutAttempt.attempt_number.desc())
            .limit(1)
            .scalar()
        )

    def get_result(self, enumerator: str) -> PayoutResult:
        return self.session.query(PayoutResult).filter(PayoutResult.enumerator == enumerator).first()

    def add_attempt(self, attempt: PayoutAttempt) -> None:
        self.session.add(attempt)
        self.session.flush()

    def count_by_account_and_status(self, account_key: str, status_id: int) -> int:
        return (
            self.session.query(func.count(Payout.id))
            .filter(Payout.account_key == account_key, Payout.status_id == status_id)
            .scalar()
        )

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
