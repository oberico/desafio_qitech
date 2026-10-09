from controllers.base_controller import BaseController
from dtos import PaymentDTO
from errors import IdempotencyKeyReused, InvalidAmount, NotFoundPayment
from repositories import PaymentRepository
from utils.payload_hash import payload_hash


class PaymentController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.payment_repository = PaymentRepository(self.context)

    def create(self, payment_data: dict, idempotency_key: str) -> tuple:
        amount_minor = payment_data["amount_minor"]

        if amount_minor <= 0:
            raise InvalidAmount(amount_minor)

        request_hash = payload_hash(self._meaningful_fields(payment_data))
        payment = self.payment_repository.build(payment_data, idempotency_key, request_hash)

        if self.payment_repository.try_insert(payment):
            payment_dto = PaymentDTO.obj_to_dict(payment)
            self.session.commit()
            return payment_dto, True

        existing = self.payment_repository.get_by_idempotency_key(payment_data["company_key"], idempotency_key)

        if existing.payload_hash != request_hash:
            raise IdempotencyKeyReused(idempotency_key)

        return PaymentDTO.obj_to_dict(existing), False

    def get_by_key(self, payment_key: str) -> dict:
        payment = self.payment_repository.get_by_key(payment_key)

        if payment is None:
            raise NotFoundPayment(payment_key)

        return PaymentDTO.obj_to_dict(payment)

    def _meaningful_fields(self, payment_data: dict) -> dict:
        method = payment_data.get("method")
        return {
            "company_key": payment_data["company_key"].lower(),
            "account_key": payment_data["account_key"].lower(),
            "amount_minor": int(payment_data["amount_minor"]),
            "origin": payment_data["origin"].lower(),
            "method": method.lower() if method else None,
        }
