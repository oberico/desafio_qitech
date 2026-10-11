from sqlalchemy.orm import Session

from models import PaymentMethod


class PaymentMethodRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_latest(self, enumerator: str) -> PaymentMethod:
        return (
            self.session.query(PaymentMethod)
            .filter(PaymentMethod.enumerator == enumerator)
            .order_by(PaymentMethod.version.desc())
            .first()
        )

    def get_locked_by_id(self, method_id: int) -> PaymentMethod:
        return (
            self.session.query(PaymentMethod)
            .filter(PaymentMethod.id == method_id)
            .with_for_update()
            .populate_existing()
            .first()
        )

    def add(self, method: PaymentMethod) -> None:
        self.session.add(method)
        self.session.flush()
