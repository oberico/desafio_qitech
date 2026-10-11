import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from constants import SCHEMAS_DIR
from connectors import BankConnector
from controllers.base_controller import BaseController
from dtos import PaymentDTO
from errors import (
    AccountNotActive,
    BankUnavailable,
    CompanyWithoutAccount,
    IdempotencyKeyReused,
    InvalidAmount,
    NotFoundCompany,
    NotFoundPayment,
)
from models import Payment, PaymentStatus
from repositories import PaymentRepository
from utils.payload_hash import payload_hash
from utils.schema_handler import validate_json

POST_PAYMENT_SCHEMA = os.path.join(SCHEMAS_DIR, "post_payment.json")
ACTIVE_ACCOUNT_STATUS = "active"
MAX_AMOUNT_MINOR = 9223372036854775807


class PaymentController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)
        self.bank_connector = BankConnector()

    def create(self, payload: dict, idempotency_key: str, client_key: str, companies: list) -> tuple:
        validate_json(payload, POST_PAYMENT_SCHEMA)
        account_key = self._authorized_account_key(payload["company_key"], companies)

        if not 0 < payload["amount_minor"] <= MAX_AMOUNT_MINOR:
            raise InvalidAmount(payload["amount_minor"])

        method = self.payment_repository.get_method(payload["method"])
        status = self.payment_repository.get_status(PaymentStatus.HELD)

        payment = Payment(
            payment_key=str(uuid4()),
            client_key=client_key,
            company_key=payload["company_key"].lower(),
            account_key=account_key,
            method=method,
            status=status,
            amount_minor=payload["amount_minor"],
            fee_bps=method.fee_bps,
            release_at=datetime.now(timezone.utc) + timedelta(hours=method.release_window_hours),
            idempotency_key=idempotency_key,
            payload_hash=payload_hash(self._meaningful_fields(payload)),
        )
        if self.payment_repository.try_create(payment):
            payment.transaction_key = self._post_receipt(payment)
            payment_dto = PaymentDTO.obj_to_dict(payment)
            self.session.commit()
            return payment_dto, True

        existing = self.payment_repository.get_by_idempotency_key(payment.company_key, idempotency_key)

        if existing.payload_hash != payment.payload_hash:
            raise IdempotencyKeyReused(idempotency_key)

        return PaymentDTO.obj_to_dict(existing), False

    def get_by_key(self, payment_key: str, client_key: str) -> dict:
        payment = self.payment_repository.get_by_key(payment_key, client_key)

        if payment is None:
            raise NotFoundPayment(payment_key)

        return PaymentDTO.obj_to_dict(payment)

    def _post_receipt(self, payment: Payment) -> str:
        receipt = {
            "type": "receipt",
            "entries": [
                {"account_code": "reserves", "debit_minor": payment.amount_minor},
                {"account_code": "in_transit", "credit_minor": payment.amount_minor},
            ],
        }
        try:
            transaction = self.bank_connector.post_ledger_transaction(
                receipt, f"receipt:{payment.company_key}:{payment.idempotency_key}"
            )
        except BankUnavailable:
            self.session.rollback()
            raise
        return transaction["transaction_key"]

    @staticmethod
    def _authorized_account_key(company_key: str, companies: list) -> str:
        company = next((item for item in companies if item["company_key"] == company_key.lower()), None)
        if company is None:
            raise NotFoundCompany(company_key)
        if company["account_key"] is None:
            raise CompanyWithoutAccount()
        if company["account_status"] != ACTIVE_ACCOUNT_STATUS:
            raise AccountNotActive()
        return company["account_key"]

    def _meaningful_fields(self, payload: dict) -> dict:
        return {
            "company_key": payload["company_key"].lower(),
            "amount_minor": payload["amount_minor"],
            "method": payload["method"],
        }
