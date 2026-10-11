import os
from datetime import datetime, timezone

from connectors import BankConnector
from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from errors import BankUnavailable, InvalidSchema
from models import Payment, PaymentStatus, PaymentStatusEvent
from repositories import PaymentRepository, PaymentTransitionRepository
from utils.fee import split_fee
from utils.schema_handler import validate_json

POST_SETTLEMENT_SCHEMA = os.path.join(SCHEMAS_DIR, "post_settlement.json")
SETTLEMENT_REASON = "settlement"


class SettlementController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)
        self.transition_repository = PaymentTransitionRepository(session)
        self.bank_connector = BankConnector()

    def run(self, payload: dict) -> dict:
        payload = payload or {}
        validate_json(payload, POST_SETTLEMENT_SCHEMA)
        as_of = self._resolve_as_of(payload)

        held_id = self.payment_repository.get_status(PaymentStatus.HELD).id
        settled_id = self.payment_repository.get_status(PaymentStatus.SETTLED).id
        due_ids = self.payment_repository.list_due_ids(held_id, as_of)
        self.session.rollback()

        settled, deferred = [], []
        for payment_id in due_ids:
            outcome = self._release(payment_id, held_id, settled_id, as_of)
            if outcome is not None:
                payment_key, released = outcome
                (settled if released else deferred).append(payment_key)

        return {"as_of": as_of.isoformat(), "settled": settled, "deferred": deferred}

    def _release(self, payment_id: int, held_id: int, settled_id: int, as_of: datetime):
        payment = self.payment_repository.get_locked_by_id(payment_id)
        payment_key = payment.payment_key

        if payment.status_id != held_id or not self.transition_repository.is_allowed(held_id, settled_id):
            self.session.rollback()
            return None

        try:
            self.bank_connector.post_ledger_transaction(
                self._settlement_payload(payment), f"settlement:{payment_key}"
            )
        except BankUnavailable:
            self.session.rollback()
            return payment_key, False

        payment.status_id = settled_id
        self.payment_repository.add_status_event(
            PaymentStatusEvent(
                payment_id=payment_id,
                status_id=settled_id,
                reason=SETTLEMENT_REASON,
                event_datetime=as_of,
            )
        )
        self.session.commit()
        return payment_key, True

    @staticmethod
    def _settlement_payload(payment: Payment) -> dict:
        fee_minor, net_minor = split_fee(payment.amount_minor, payment.fee_bps)
        debits, credits = [], []
        if net_minor > 0:
            debits.append({"account_code": "in_transit", "debit_minor": net_minor})
            credits.append({"account_key": payment.account_key, "credit_minor": net_minor})
        if fee_minor > 0:
            debits.append({"account_code": "in_transit", "debit_minor": fee_minor})
            credits.append({"account_code": "revenue", "credit_minor": fee_minor})
        return {
            "type": "settlement",
            "settles_transaction_key": payment.transaction_key,
            "entries": debits + credits,
        }

    @staticmethod
    def _resolve_as_of(payload: dict) -> datetime:
        if "as_of" not in payload:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(payload["as_of"])
        except ValueError as error:
            raise InvalidSchema("as_of: not a valid ISO 8601 instant") from error
