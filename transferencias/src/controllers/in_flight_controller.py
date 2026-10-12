from controllers.base_controller import BaseController
from dtos import InFlightDTO
from models import PaymentStatus, PayoutStatus
from repositories import PaymentRepository, PayoutRepository


class InFlightController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)
        self.payout_repository = PayoutRepository(session)

    def summarize(self, account_key: str) -> dict:
        account_key = account_key.lower()
        held = self.payment_repository.get_status(PaymentStatus.HELD)
        pending = self.payout_repository.get_status(PayoutStatus.PENDING)
        return InFlightDTO.to_dict(
            self.payment_repository.count_by_account_and_status(account_key, held.id),
            self.payout_repository.count_by_account_and_status(account_key, pending.id),
        )
