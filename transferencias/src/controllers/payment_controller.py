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
    InvalidSchema,
    NotFoundCompany,
    NotFoundPayment,
    PaymentAlreadyRefunded,
    PaymentOutsideWindow,
)
from models import Payment, PaymentStatus, PaymentStatusEvent
from repositories import PaymentRepository, PaymentTransitionRepository
from utils.pagination import build_page, page_size
from utils.payload_hash import payload_hash
from utils.schema_handler import validate_json

POST_PAYMENT_SCHEMA = os.path.join(SCHEMAS_DIR, "post_payment.json")
GET_PAYMENTS_SCHEMA = os.path.join(SCHEMAS_DIR, "get_payments.json")
ACTIVE_ACCOUNT_STATUS = "active"
MAX_AMOUNT_MINOR = 9223372036854775807
REFUND_REASON = "refund"


class PaymentController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)
        self.transition_repository = PaymentTransitionRepository(session)
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

    def list_page(self, query: dict, client_key: str) -> dict:
        validate_json(query, GET_PAYMENTS_SCHEMA)
        size = page_size(query)
        before_id = self._cursor_id(query.get("cursor"), client_key)

        payments = self.payment_repository.list_newest_first(client_key, size + 1, before_id, query.get("status"))
        return build_page(payments, size, PaymentDTO.obj_to_dict, lambda payment: payment.payment_key)

    def _cursor_id(self, cursor: str, client_key: str) -> int:
        if cursor is None:
            return None
        payment = self.payment_repository.get_by_key(cursor.lower(), client_key)
        if payment is None:
            raise InvalidSchema(f"cursor: {cursor} does not point to an existing item")
        return payment.id

    def refund(self, payment_key: str, client_key: str) -> dict:
        payment = self.payment_repository.get_locked_by_key(payment_key, client_key)

        if payment is None:
            raise NotFoundPayment(payment_key)

        held = self.payment_repository.get_status(PaymentStatus.HELD)
        refunded = self.payment_repository.get_status(PaymentStatus.REFUNDED)

        if payment.status_id == refunded.id:
            self.session.rollback()
            raise PaymentAlreadyRefunded()
        if payment.status_id != held.id or not self.transition_repository.is_allowed(held.id, refunded.id):
            self.session.rollback()
            raise PaymentOutsideWindow()

        self._post_refund(payment)
        payment.status = refunded
        self.payment_repository.add_status_event(
            PaymentStatusEvent(
                payment_id=payment.id,
                status_id=refunded.id,
                reason=REFUND_REASON,
                event_datetime=datetime.now(timezone.utc),
            )
        )
        payment_dto = PaymentDTO.obj_to_dict(payment)
        self.session.commit()
        return payment_dto

    def _post_refund(self, payment: Payment) -> None:
        refund = {
            "type": "refund",
            "reverses_transaction_key": payment.transaction_key,
            "entries": [
                {"account_code": "in_transit", "debit_minor": payment.amount_minor},
                {"account_code": "reserves", "credit_minor": payment.amount_minor},
            ],
        }
        try:
            self.bank_connector.post_ledger_transaction(refund, f"refund:{payment.payment_key}")
        except BankUnavailable:
            self.session.rollback()
            raise

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
