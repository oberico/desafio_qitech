import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import PaymentDTO
from errors import IdempotencyKeyReused, InvalidAmount, NotFoundPayment
from models import Payment, PaymentStatus
from repositories import PaymentRepository
from utils.payload_hash import payload_hash
from utils.schema_handler import validate_json

POST_PAYMENT_SCHEMA = os.path.join(SCHEMAS_DIR, "post_payment.json")


class PaymentController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)

    def create(self, payload: dict, idempotency_key: str) -> tuple:
        validate_json(payload, POST_PAYMENT_SCHEMA)

        if payload["amount_minor"] <= 0:
            raise InvalidAmount(payload["amount_minor"])

        method = self.payment_repository.get_method(payload["method"])
        status = self.payment_repository.get_status(PaymentStatus.HELD)

        payment = Payment(
            payment_key=str(uuid4()),
            company_key=payload["company_key"].lower(),
            account_key=payload["account_key"].lower(),
            method=method,
            status=status,
            amount_minor=payload["amount_minor"],
            fee_bps=method.fee_bps,
            release_at=datetime.now(timezone.utc) + timedelta(hours=method.release_window_hours),
            idempotency_key=idempotency_key,
            payload_hash=payload_hash(self._meaningful_fields(payload)),
        )
        if self.payment_repository.try_create(payment):
            payment_dto = PaymentDTO.obj_to_dict(payment)
            self.session.commit()
            return payment_dto, True

        existing = self.payment_repository.get_by_idempotency_key(payment.company_key, idempotency_key)

        if existing.payload_hash != payment.payload_hash:
            raise IdempotencyKeyReused(idempotency_key)

        return PaymentDTO.obj_to_dict(existing), False

    def get_by_key(self, payment_key: str) -> dict:
        payment = self.payment_repository.get_by_key(payment_key)

        if payment is None:
            raise NotFoundPayment(payment_key)

        return PaymentDTO.obj_to_dict(payment)

    def _meaningful_fields(self, payload: dict) -> dict:
        return {
            "company_key": payload["company_key"].lower(),
            "account_key": payload["account_key"].lower(),
            "amount_minor": payload["amount_minor"],
            "method": payload["method"],
        }
