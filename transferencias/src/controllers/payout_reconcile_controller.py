import os
from datetime import datetime, timedelta

from connectors import BankConnector, InterbankConnector
from connectors.interbank_connector import CONFIRMED, REJECTED, TIMEOUT
from constants import PAYOUT_BACKOFF_BASE_SECONDS, PAYOUT_MAX_ATTEMPTS, PAYOUT_MAX_PER_RUN, SCHEMAS_DIR
from controllers.base_controller import BaseController
from errors import BankUnavailable
from models import Payout, PayoutAttempt, PayoutStatus, PayoutStatusEvent
from repositories import PayoutRepository, PayoutTransitionRepository
from utils.as_of import resolve_as_of
from utils.schema_handler import validate_json

POST_PAYOUT_RECONCILE_SCHEMA = os.path.join(SCHEMAS_DIR, "post_payout_reconcile.json")
SETTLEMENT_REASON = "settlement"
FAILURE_REASONS = {REJECTED: "interbank_refused", TIMEOUT: "interbank_timeout"}

ATTEMPT = "attempt"
SETTLE = "settle"
REVERSE = "reverse"
WAIT = "wait"

SETTLED = "settled"
FAILED = "failed"
PENDING = "pending"
SKIPPED = "skipped"
CONTINUE = "continue"


class PayoutReconcileController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payout_repository = PayoutRepository(session)
        self.transition_repository = PayoutTransitionRepository(session)
        self.bank_connector = BankConnector()
        self.interbank_connector = InterbankConnector()

    def run(self, payload: dict) -> dict:
        payload = payload or {}
        validate_json(payload, POST_PAYOUT_RECONCILE_SCHEMA)
        as_of = resolve_as_of(payload)

        self.pending_id = self.payout_repository.get_status(PayoutStatus.PENDING).id
        snapshots = self.payout_repository.list_pending_snapshots(self.pending_id)
        self.session.rollback()

        actionable_ids = [
            snapshot.id
            for snapshot in snapshots
            if self._phase(snapshot.attempts, snapshot.last_result, snapshot.last_attempt_at, as_of) != WAIT
        ]

        summary = {SETTLED: [], FAILED: [], PENDING: []}
        for payout_id in actionable_ids[:PAYOUT_MAX_PER_RUN]:
            payout_key, outcome = self._advance(payout_id, as_of)
            if outcome in summary:
                summary[outcome].append(payout_key)

        return {"as_of": as_of.isoformat(), **summary}

    def _advance(self, payout_id: int, as_of: datetime) -> tuple:
        while True:
            payout_key, outcome = self._step(payout_id, as_of)
            if outcome != CONTINUE:
                return payout_key, outcome

    def _step(self, payout_id: int, as_of: datetime) -> tuple:
        payout = self.payout_repository.get_locked_by_id(payout_id)
        payout_key = payout.payout_key

        if payout.status_id != self.pending_id:
            self.session.rollback()
            return payout_key, SKIPPED

        attempts = self.payout_repository.count_attempts(payout.id)
        last_result = self.payout_repository.get_last_attempt_result(payout.id)
        phase = self._phase(attempts, last_result, payout.last_attempt_at, as_of)

        if phase == WAIT:
            self.session.rollback()
            return payout_key, SKIPPED
        if phase == ATTEMPT:
            return payout_key, self._attempt(payout, attempts, as_of)
        if phase == SETTLE:
            return payout_key, self._settle(payout, as_of)
        return payout_key, self._reverse(payout, last_result, as_of)

    def _attempt(self, payout: Payout, attempts: int, as_of: datetime) -> str:
        result = self.interbank_connector.transfer(
            payout.payout_key, payout.amount_minor, payout.purpose.enumerator, payout.destination
        )
        self.payout_repository.add_attempt(
            PayoutAttempt(
                payout_id=payout.id,
                result_id=self.payout_repository.get_result(result.outcome).id,
                attempt_number=attempts + 1,
                created_at=as_of,
            )
        )
        payout.last_attempt_at = as_of
        self.session.commit()

        if result.outcome == TIMEOUT and attempts + 1 < PAYOUT_MAX_ATTEMPTS:
            return PENDING
        return CONTINUE

    def _settle(self, payout: Payout, as_of: datetime) -> str:
        payload = {
            "type": "settlement",
            "settles_transaction_key": payout.transaction_key,
            "entries": [
                {"account_code": "in_transit", "debit_minor": payout.amount_minor},
                {"account_code": "reserves", "credit_minor": payout.amount_minor},
            ],
        }
        if not self._post_to_bank(payload, f"settlement:{payout.payout_key}"):
            return PENDING
        return self._finish(payout, SETTLED, SETTLEMENT_REASON, None, as_of)

    def _reverse(self, payout: Payout, last_result: str, as_of: datetime) -> str:
        entries = []
        if payout.fee_minor > 0:
            entries.append({"account_code": "revenue", "debit_minor": payout.fee_minor})
        entries.append({"account_code": "in_transit", "debit_minor": payout.amount_minor})
        entries.append({"account_key": payout.account_key, "credit_minor": payout.amount_minor + payout.fee_minor})
        payload = {"type": "reversal", "reverses_transaction_key": payout.transaction_key, "entries": entries}
        if not self._post_to_bank(payload, f"reversal:{payout.payout_key}"):
            return PENDING
        reason = FAILURE_REASONS[last_result]
        return self._finish(payout, FAILED, reason, reason, as_of)

    def _post_to_bank(self, payload: dict, idempotency_key: str) -> bool:
        try:
            self.bank_connector.post_ledger_transaction(payload, idempotency_key)
        except BankUnavailable:
            self.session.rollback()
            return False
        return True

    def _finish(self, payout: Payout, target: str, reason: str, failure_reason: str, as_of: datetime) -> str:
        target_status = self.payout_repository.get_status(target)
        if not self.transition_repository.is_allowed(payout.status_id, target_status.id):
            self.session.rollback()
            return SKIPPED

        payout.status_id = target_status.id
        payout.failure_reason = failure_reason
        self.payout_repository.add_status_event(
            PayoutStatusEvent(
                payout_id=payout.id,
                status_id=target_status.id,
                reason=reason,
                event_datetime=as_of,
            )
        )
        self.session.commit()
        return target

    @staticmethod
    def _phase(attempts: int, last_result: str, last_attempt_at: datetime, as_of: datetime) -> str:
        if attempts == 0:
            return ATTEMPT
        if last_result == CONFIRMED:
            return SETTLE
        if last_result == REJECTED or attempts >= PAYOUT_MAX_ATTEMPTS:
            return REVERSE
        wait = timedelta(seconds=PAYOUT_BACKOFF_BASE_SECONDS * 2 ** (attempts - 1))
        return ATTEMPT if as_of >= last_attempt_at + wait else WAIT
