import os
from collections import defaultdict

from sqlalchemy.exc import IntegrityError

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import LedgerTransactionDTO
from errors import (
    AccountNotFound,
    IdempotencyKeyReused,
    InvalidTransactionReference,
    InsufficientFunds,
    LedgerAccountNotActive,
    LedgerTransactionNotFound,
    TransactionAlreadyConsumed,
    UnbalancedEntries,
)
from models import AccountStatus, TransactionStatus, TransactionType
from repositories import LedgerRepository
from utils.payload_hash import payload_hash
from utils.schema_handler import validate_json

POST_LEDGER_TRANSACTION_SCHEMA = os.path.join(SCHEMAS_DIR, "post_ledger_transaction.json")
IDEMPOTENCY_CONSTRAINT = "uq_transaction_idempotency_key"
CONSUMPTION_CONSTRAINTS = {"uq_transaction_settles", "uq_transaction_reverses"}
BORN_PENDING = {TransactionType.PAYOUT}
REFERENCEABLE_TYPES = {
    TransactionType.SETTLEMENT: {TransactionType.RECEIPT, TransactionType.PAYOUT},
    TransactionType.REFUND: {TransactionType.RECEIPT},
    TransactionType.REVERSAL: {TransactionType.PAYOUT},
}


class LedgerController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.ledger_repository = LedgerRepository(session)

    def create_transaction(self, payload: dict, idempotency_key: str) -> tuple:
        validate_json(payload, POST_LEDGER_TRANSACTION_SCHEMA)
        request_hash = payload_hash(self._meaningful_fields(payload))

        existing = self.ledger_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return self._replay(existing, request_hash)

        legs = self._resolve_legs(payload["entries"])
        self._ensure_balanced(legs)
        settles = self._resolve_transaction(payload.get("settles_transaction_key"))
        reverses = self._resolve_transaction(payload.get("reverses_transaction_key"))
        self._ensure_referenceable(payload["type"], settles or reverses)
        self._ensure_not_consumed(settles)
        self._ensure_not_consumed(reverses)
        self._ensure_funds(legs)

        try:
            transaction = self.ledger_repository.create(
                type_enumerator=payload["type"],
                status_enumerator=self._initial_status(payload["type"]),
                idempotency_key=idempotency_key,
                payload_hash=request_hash,
                legs=legs,
                settles_transaction_id=settles.id if settles else None,
                reverses_transaction_id=reverses.id if reverses else None,
            )
        except IntegrityError as error:
            self.session.rollback()
            return self._handle_conflict(error, payload, idempotency_key, request_hash)

        transaction_dto = LedgerTransactionDTO.obj_to_dict(transaction)
        self.session.commit()
        return transaction_dto, True

    def _resolve_legs(self, entries: list) -> list:
        return [
            {
                "account": self._resolve_account(entry),
                "debit_minor": entry.get("debit_minor", 0),
                "credit_minor": entry.get("credit_minor", 0),
            }
            for entry in entries
        ]

    def _resolve_account(self, entry: dict):
        if "account_code" in entry:
            reference = entry["account_code"]
            account = self.ledger_repository.get_account_by_code(reference)
        else:
            reference = entry["account_key"]
            account = self.ledger_repository.get_account_by_key(reference)

        if account is None:
            raise AccountNotFound(reference)
        if account.status.enumerator != AccountStatus.ACTIVE:
            raise LedgerAccountNotActive(reference)
        return account

    def _ensure_balanced(self, legs: list) -> None:
        total_debit = sum(leg["debit_minor"] for leg in legs)
        total_credit = sum(leg["credit_minor"] for leg in legs)
        if total_debit != total_credit:
            raise UnbalancedEntries(total_debit, total_credit)

    def _resolve_transaction(self, transaction_key: str):
        if transaction_key is None:
            return None
        transaction = self.ledger_repository.get_transaction_by_key(transaction_key)
        if transaction is None:
            raise LedgerTransactionNotFound(transaction_key)
        return transaction

    def _ensure_referenceable(self, type_enumerator: str, target) -> None:
        if target is None:
            return
        if target.type.enumerator not in REFERENCEABLE_TYPES[type_enumerator]:
            raise InvalidTransactionReference(target.transaction_key, target.type.enumerator)

    def _ensure_not_consumed(self, transaction) -> None:
        if transaction is None:
            return
        self.ledger_repository.lock_transaction(transaction.id)
        if self.ledger_repository.is_consumed(transaction.id):
            raise TransactionAlreadyConsumed(transaction.transaction_key)

    def _ensure_funds(self, legs: list) -> None:
        debits = defaultdict(int)
        for leg in legs:
            if leg["account"].company_id is not None and leg["debit_minor"] > 0:
                debits[leg["account"].id] += leg["debit_minor"]

        for account_id in sorted(debits):
            self.ledger_repository.lock_account(account_id)
            if self.ledger_repository.balance_of(account_id) < debits[account_id]:
                raise InsufficientFunds()

    def _initial_status(self, type_enumerator: str) -> str:
        if type_enumerator in BORN_PENDING:
            return TransactionStatus.PENDING
        return TransactionStatus.SETTLED

    def _replay(self, existing, request_hash: str) -> tuple:
        if existing.payload_hash != request_hash:
            raise IdempotencyKeyReused(existing.idempotency_key)
        return LedgerTransactionDTO.obj_to_dict(existing), False

    def _handle_conflict(self, error: IntegrityError, payload: dict, idempotency_key: str, request_hash: str) -> tuple:
        constraint = self.ledger_repository.violated_constraint(error)
        if constraint == IDEMPOTENCY_CONSTRAINT:
            existing = self.ledger_repository.get_by_idempotency_key(idempotency_key)
            return self._replay(existing, request_hash)
        if constraint in CONSUMPTION_CONSTRAINTS:
            raise TransactionAlreadyConsumed(payload.get("settles_transaction_key") or payload.get("reverses_transaction_key"))
        raise error

    def _meaningful_fields(self, payload: dict) -> dict:
        entries = sorted(
            [
                entry.get("account_code", "").lower(),
                entry.get("account_key", "").lower(),
                entry.get("debit_minor", 0),
                entry.get("credit_minor", 0),
            ]
            for entry in payload["entries"]
        )
        return {
            "type": payload["type"],
            "settles_transaction_key": (payload.get("settles_transaction_key") or "").lower(),
            "reverses_transaction_key": (payload.get("reverses_transaction_key") or "").lower(),
            "entries": entries,
        }
