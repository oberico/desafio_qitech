from collections import defaultdict

from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from dtos import LedgerTransactionDTO
from errors import (
    IdempotencyKeyReused,
    InsufficientFunds,
    LedgerAccountNotFound,
    LedgerTransactionNotFound,
    TransactionAlreadyReversed,
    TransactionAlreadySettled,
    UnbalancedEntries,
)
from models import TransactionStatus, TransactionType
from repositories import LedgerRepository
from utils.payload_hash import payload_hash

IDEMPOTENCY_CONSTRAINT = "uq_transaction_idempotency_key"
SETTLES_CONSTRAINT = "uq_transaction_settles"
REVERSES_CONSTRAINT = "uq_transaction_reverses"

BORN_PENDING = {TransactionType.PAYOUT}


class LedgerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.ledger_repository = LedgerRepository(self.context)

    def post_transaction(self, transaction_data: dict) -> tuple:
        idempotency_key = transaction_data["idempotency_key"]
        request_hash = payload_hash(self._meaningful_fields(transaction_data))

        legs = self._resolve_legs(transaction_data["entries"])
        self._ensure_balanced(legs)
        settles = self._resolve_transaction(transaction_data.get("settles"))
        reverses = self._resolve_transaction(transaction_data.get("reverses"))

        client_debits = self._client_debits(legs)

        for account_id in sorted(client_debits):
            self.ledger_repository.lock_account(account_id)

        existing = self.ledger_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return self._replay(existing, request_hash)

        for account_id in sorted(client_debits):
            balance = self.ledger_repository.balance_of(account_id)
            if balance < client_debits[account_id]:
                self.session.rollback()
                raise InsufficientFunds()

        type_enumerator = transaction_data["type"].lower()

        try:
            transaction = self.ledger_repository.create(
                type_enumerator=type_enumerator,
                status_enumerator=self._initial_status(type_enumerator),
                idempotency_key=idempotency_key,
                payload_hash=request_hash,
                legs=legs,
                settles_transaction_id=settles.id if settles else None,
                reverses_transaction_id=reverses.id if reverses else None,
            )
        except IntegrityError as error:
            self.session.rollback()
            return self._handle_conflict(error, idempotency_key, request_hash)

        transaction_dto = LedgerTransactionDTO.obj_to_dict(transaction)
        self.session.commit()
        return transaction_dto, True

    def _resolve_legs(self, entries: list) -> list:
        legs = []
        for entry in entries:
            account = self._resolve_account(entry)
            legs.append(
                {
                    "account": account,
                    "debit_minor": int(entry.get("debit_minor", 0)),
                    "credit_minor": int(entry.get("credit_minor", 0)),
                }
            )
        return legs

    def _resolve_account(self, entry: dict):
        if "account_code" in entry:
            account = self.ledger_repository.get_account_by_code(entry["account_code"])
            reference = entry["account_code"]
        else:
            account = self.ledger_repository.get_account_by_key(entry["account_key"])
            reference = entry["account_key"]

        if account is None:
            raise LedgerAccountNotFound(reference)
        return account

    def _resolve_transaction(self, transaction_key: str):
        if transaction_key is None:
            return None
        transaction = self.ledger_repository.get_transaction_by_key(transaction_key)
        if transaction is None:
            raise LedgerTransactionNotFound(transaction_key)
        return transaction

    def _ensure_balanced(self, legs: list) -> None:
        total_debit = sum(leg["debit_minor"] for leg in legs)
        total_credit = sum(leg["credit_minor"] for leg in legs)
        if len(legs) < 2 or total_debit != total_credit:
            raise UnbalancedEntries(total_debit, total_credit)

    def _client_debits(self, legs: list) -> dict:
        debits = defaultdict(int)
        for leg in legs:
            account = leg["account"]
            if account.company_id is not None and leg["debit_minor"] > 0:
                debits[account.id] += leg["debit_minor"]
        return dict(debits)

    def _initial_status(self, type_enumerator: str) -> str:
        if type_enumerator in BORN_PENDING:
            return TransactionStatus.PENDING
        return TransactionStatus.SETTLED

    def _replay(self, existing, request_hash: str) -> tuple:
        if existing.payload_hash != request_hash:
            self.session.rollback()
            raise IdempotencyKeyReused(existing.idempotency_key)

        transaction_dto = LedgerTransactionDTO.obj_to_dict(existing)
        self.session.rollback()
        return transaction_dto, False

    def _handle_conflict(self, error: IntegrityError, idempotency_key: str, request_hash: str) -> tuple:
        constraint = self.ledger_repository.violated_constraint(error)

        if constraint == IDEMPOTENCY_CONSTRAINT:
            existing = self.ledger_repository.get_by_idempotency_key(idempotency_key)
            return self._replay(existing, request_hash)
        if constraint == SETTLES_CONSTRAINT:
            raise TransactionAlreadySettled()
        if constraint == REVERSES_CONSTRAINT:
            raise TransactionAlreadyReversed()
        raise error

    def _meaningful_fields(self, transaction_data: dict) -> dict:
        entries = sorted(
            (
                (entry.get("account_code") or "").lower(),
                (entry.get("account_key") or "").lower(),
                int(entry.get("debit_minor", 0)),
                int(entry.get("credit_minor", 0)),
            )
            for entry in transaction_data["entries"]
        )
        settles = transaction_data.get("settles")
        reverses = transaction_data.get("reverses")
        return {
            "type": transaction_data["type"].lower(),
            "settles": settles.lower() if settles else None,
            "reverses": reverses.lower() if reverses else None,
            "entries": [list(entry) for entry in entries],
        }
