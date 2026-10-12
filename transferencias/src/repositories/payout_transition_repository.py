from sqlalchemy.orm import Session

from models import PayoutTransition


class PayoutTransitionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def is_allowed(self, from_status_id: int, to_status_id: int) -> bool:
        return (
            self.session.query(PayoutTransition.id)
            .filter(
                PayoutTransition.from_status_id == from_status_id,
                PayoutTransition.to_status_id == to_status_id,
            )
            .first()
            is not None
        )
