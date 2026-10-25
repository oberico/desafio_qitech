from sqlalchemy.orm import Session

from models import PayoutFee


class PayoutFeeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_latest(self) -> PayoutFee:
        return self.session.query(PayoutFee).order_by(PayoutFee.version.desc()).first()

    def get_locked_by_id(self, fee_id: int) -> PayoutFee:
        return (
            self.session.query(PayoutFee)
            .filter(PayoutFee.id == fee_id)
            .with_for_update()
            .populate_existing()
            .first()
        )

    def add(self, fee: PayoutFee) -> None:
        self.session.add(fee)
        self.session.flush()
