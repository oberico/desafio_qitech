import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from constants import SCHEMAS_DIR
from connectors import BankConnector
from controllers.base_controller import BaseController
from dtos import PayoutDTO
from errors import (
    AccountNotActive,
    BankRefused,
    BankUnavailable,
    IdempotencyKeyReused,
    InvalidAmount,
    NotFoundCompany,
    NotFoundPayout,
    ValueOutOfRange,
)
from models import Payout, PayoutStatus, PayoutStatusEvent
from repositories import PayoutFeeRepository, PayoutRepository
from utils.fee import split_fee
from utils.payload_hash import payload_hash
from utils.schema_handler import validate_json

POST_PAYOUT_SCHEMA = os.path.join(SCHEMAS_DIR, "post_payout.json")
ACTIVE_ACCOUNT_STATUS = "active"
MAX_AMOUNT_MINOR = 9223372036854775807
MAX_DESTINATION_BYTES = 4096
CREATED_REASON = "created"


class PayoutController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payout_repository = PayoutRepository(session)
        self.payout_fee_repository = PayoutFeeRepository(session)
        self.bank_connector = BankConnector()

    def create(self, payload: dict, idempotency_key: str, companies: list) -> tuple:
        validate_json(payload, POST_PAYOUT_SCHEMA)
        self._ensure_destination_size(payload["destination"])
        company = self._authorized_company(payload["account_key"], companies)

        fee = self.payout_fee_repository.get_latest()
        if not 0 < payload["amount_minor"] <= MAX_AMOUNT_MINOR:
            raise InvalidAmount(payload["amount_minor"], MAX_AMOUNT_MINOR)

        fee_minor = split_fee(payload["amount_minor"], fee.fee_bps)[0]
        if payload["amount_minor"] + fee_minor > MAX_AMOUNT_MINOR:
            raise InvalidAmount(payload["amount_minor"] + fee_minor, MAX_AMOUNT_MINOR)

        purpose = self.payout_repository.get_purpose(payload["purpose"])
        status = self.payout_repository.get_status(PayoutStatus.PENDING)

        payout = Payout(
            payout_key=str(uuid4()),
            company_key=company["company_key"],
            account_key=company["account_key"],
            purpose=purpose,
            fee_id=fee.id,
            destination=payload["destination"],
            status=status,
            amount_minor=payload["amount_minor"],
            fee_bps=fee.fee_bps,
            fee_minor=fee_minor,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash(self._meaningful_fields(payload)),
        )
        if self.payout_repository.try_create(payout):
            payout.transaction_key = self._post_payout_debit(payout)
            self.payout_repository.add_status_event(
                PayoutStatusEvent(
                    payout_id=payout.id,
                    status_id=status.id,
                    reason=CREATED_REASON,
                    event_datetime=datetime.now(timezone.utc),
                )
            )
            payout_dto = PayoutDTO.obj_to_dict(payout, 0)
            self.session.commit()
            return payout_dto, True

        existing = self.payout_repository.get_by_idempotency_key(payout.company_key, idempotency_key)

        if existing.payload_hash != payout.payload_hash:
            raise IdempotencyKeyReused(idempotency_key)

        return self._to_dict(existing), False

    def get_by_key(self, payout_key: str, companies: list) -> dict:
        company_keys = [company["company_key"] for company in companies]
        payout = self.payout_repository.get_by_key(payout_key, company_keys)

        if payout is None:
            raise NotFoundPayout(payout_key)

        return self._to_dict(payout)

    def _to_dict(self, payout: Payout) -> dict:
        return PayoutDTO.obj_to_dict(payout, self.payout_repository.count_attempts(payout.id))

    def _post_payout_debit(self, payout: Payout) -> str:
        entries = [
            {"account_key": payout.account_key, "debit_minor": payout.amount_minor + payout.fee_minor},
            {"account_code": "in_transit", "credit_minor": payout.amount_minor},
        ]
        if payout.fee_minor > 0:
            entries.append({"account_code": "revenue", "credit_minor": payout.fee_minor})
        debit = {"type": "payout", "entries": entries}
        try:
            transaction = self.bank_connector.post_ledger_transaction(
                debit, f"payout:{payout.company_key}:{payout.idempotency_key}", forward_refusals=True
            )
        except (BankUnavailable, BankRefused):
            self.session.rollback()
            raise
        return transaction["transaction_key"]

    @staticmethod
    def _ensure_destination_size(destination: dict) -> None:
        serialized = json.dumps(destination, separators=(",", ":"), ensure_ascii=False)
        if len(serialized.encode("utf-8")) > MAX_DESTINATION_BYTES:
            raise ValueOutOfRange(
                "destination",
                f"destination: exceeds {MAX_DESTINATION_BYTES} bytes when serialized",
                f"deve ter no máximo {MAX_DESTINATION_BYTES} bytes",
            )

    @staticmethod
    def _authorized_company(account_key: str, companies: list) -> dict:
        company = next(
            (item for item in companies if item["account_key"] and item["account_key"] == account_key.lower()),
            None,
        )
        if company is None:
            raise NotFoundCompany(account_key)
        if company["account_status"] != ACTIVE_ACCOUNT_STATUS:
            raise AccountNotActive()
        return company

    @staticmethod
    def _meaningful_fields(payload: dict) -> dict:
        return {
            "account_key": payload["account_key"].lower(),
            "purpose": payload["purpose"],
            "amount_minor": payload["amount_minor"],
            "destination": payload["destination"],
        }
