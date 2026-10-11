import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import PaymentMethodDTO
from models import PaymentMethod
from repositories import PaymentMethodRepository
from utils.schema_handler import validate_json

PUT_PAYMENT_METHOD_SCHEMA = os.path.join(SCHEMAS_DIR, "put_payment_method.json")
PAYMENT_METHOD_ENUMERATOR_SCHEMA = os.path.join(SCHEMAS_DIR, "payment_method_enumerator.json")


class PaymentMethodController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_method_repository = PaymentMethodRepository(session)

    def change_terms(self, enumerator: str, payload: dict) -> tuple:
        validate_json(enumerator, PAYMENT_METHOD_ENUMERATOR_SCHEMA)
        validate_json(payload, PUT_PAYMENT_METHOD_SCHEMA)

        current = self._lock_latest(enumerator)

        if (current.fee_bps, current.release_window_hours) == (payload["fee_bps"], payload["release_window_hours"]):
            return PaymentMethodDTO.obj_to_dict(current), False

        method = PaymentMethod(
            enumerator=enumerator,
            version=current.version + 1,
            fee_bps=payload["fee_bps"],
            release_window_hours=payload["release_window_hours"],
        )
        self.payment_method_repository.add(method)
        self.session.refresh(method)
        method_dto = PaymentMethodDTO.obj_to_dict(method)
        self.session.commit()
        return method_dto, True

    def _lock_latest(self, enumerator: str) -> PaymentMethod:
        locked = self.payment_method_repository.get_locked_by_id(
            self.payment_method_repository.get_latest(enumerator).id
        )
        latest = self.payment_method_repository.get_latest(enumerator)
        while latest.id != locked.id:
            locked = self.payment_method_repository.get_locked_by_id(latest.id)
            latest = self.payment_method_repository.get_latest(enumerator)
        return locked
