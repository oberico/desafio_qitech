import asyncio
import json
import os
from dataclasses import dataclass

from constants import (
    DEFAULT_SCENARIO,
    FLAKY_FAILURES_BEFORE_CONFIRM,
    MOCK_TIMEOUT_SECONDS,
    SCENARIO_CONFIRM,
    SCENARIO_FLAKY,
    SCENARIO_REFUSE,
    SCENARIO_TIMEOUT,
    SCHEMAS_DIR,
)
from errors import InvalidSchema
from repositories import TransferRepository, transfer_repository
from utils.logger import get_logger
from utils.schema_handler import validate_json

logger = get_logger(__name__)

POST_TRANSFER_SCHEMA = os.path.join(SCHEMAS_DIR, "post_transfer.json")


@dataclass
class TransferOutcome:
    http_status: int
    body: dict


class TransferController:
    def __init__(self, repository: TransferRepository = transfer_repository) -> None:
        self.repository = repository

    async def create(self, raw_body: bytes) -> TransferOutcome:
        payload = self._parse(raw_body)
        validate_json(payload, POST_TRANSFER_SCHEMA)

        payout_key = payload["payout_key"].lower()
        scenario = payload["destination"].get("scenario", DEFAULT_SCENARIO)

        if scenario == SCENARIO_REFUSE:
            return self._refuse(payout_key, scenario)
        if scenario == SCENARIO_TIMEOUT:
            return await self._timeout(payout_key, scenario)
        if scenario == SCENARIO_FLAKY:
            return await self._flaky(payout_key, scenario)
        return self._confirm(payout_key, scenario)

    @staticmethod
    def _parse(raw_body: bytes) -> dict:
        try:
            return json.loads(raw_body)
        except ValueError:
            raise InvalidSchema("body: is not valid JSON")

    def _confirm(self, payout_key: str, scenario: str) -> TransferOutcome:
        transfer_id = self.repository.get_or_create_transfer_id(payout_key)
        logger.info(f"payout_key={payout_key} scenario={scenario} result=confirmed transfer_id={transfer_id}")
        return TransferOutcome(200, {"transfer_id": transfer_id, "status": "confirmed"})

    @staticmethod
    def _refuse(payout_key: str, scenario: str) -> TransferOutcome:
        logger.info(f"payout_key={payout_key} scenario={scenario} result=refused")
        return TransferOutcome(422, {"status": "refused", "reason": "destination_refused"})

    @staticmethod
    async def _timeout(payout_key: str, scenario: str, call_number: int = None) -> TransferOutcome:
        suffix = f" call={call_number}" if call_number else ""
        logger.info(f"payout_key={payout_key} scenario={scenario}{suffix} result=stalled seconds={MOCK_TIMEOUT_SECONDS}")
        await asyncio.sleep(MOCK_TIMEOUT_SECONDS)
        return TransferOutcome(504, {"status": "timeout"})

    async def _flaky(self, payout_key: str, scenario: str) -> TransferOutcome:
        call_number = self.repository.register_flaky_call(payout_key)
        if call_number <= FLAKY_FAILURES_BEFORE_CONFIRM:
            return await self._timeout(payout_key, scenario, call_number)
        return self._confirm(payout_key, f"{scenario}(call={call_number})")
