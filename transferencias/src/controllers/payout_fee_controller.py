import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import PayoutFeeDTO
from models import PayoutFee
from repositories import PayoutFeeRepository
from utils.schema_handler import validate_json

PUT_PAYOUT_FEE_SCHEMA = os.path.join(SCHEMAS_DIR, "put_payout_fee.json")


class PayoutFeeController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payout_fee_repository = PayoutFeeRepository(session)

    def change_fee(self, payload: dict) -> tuple:
        validate_json(payload, PUT_PAYOUT_FEE_SCHEMA)

        current = self._lock_latest()

        if current.fee_bps == payload["fee_bps"]:
            return PayoutFeeDTO.obj_to_dict(current), False

        fee = PayoutFee(version=current.version + 1, fee_bps=payload["fee_bps"])
        self.payout_fee_repository.add(fee)
        self.session.refresh(fee)
        fee_dto = PayoutFeeDTO.obj_to_dict(fee)
        self.session.commit()
        return fee_dto, True

    def _lock_latest(self) -> PayoutFee:
        locked = self.payout_fee_repository.get_locked_by_id(self.payout_fee_repository.get_latest().id)
        latest = self.payout_fee_repository.get_latest()
        while latest.id != locked.id:
            locked = self.payout_fee_repository.get_locked_by_id(latest.id)
            latest = self.payout_fee_repository.get_latest()
        return locked
