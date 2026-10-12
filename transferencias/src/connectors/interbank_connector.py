from dataclasses import dataclass

import requests

from constants import INTERBANK_API_URL, INTERBANK_TIMEOUT_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)

CONFIRMED = "confirmed"
REJECTED = "rejected"
TIMEOUT = "timeout"


@dataclass(frozen=True)
class InterbankResult:
    outcome: str


class InterbankConnector:
    def transfer(self, payout_key: str, amount_minor: int, purpose: str, destination: dict) -> InterbankResult:
        body = {
            "payout_key": payout_key,
            "amount_minor": amount_minor,
            "purpose": purpose,
            "destination": destination,
        }
        try:
            response = requests.post(
                f"{INTERBANK_API_URL}/interbank/transfers",
                json=body,
                timeout=INTERBANK_TIMEOUT_SECONDS,
            )
        except requests.exceptions.RequestException as error:
            logger.warning(f"payout_key={payout_key} interbank unreachable: {error.__class__.__name__}")
            return InterbankResult(TIMEOUT)

        if response.status_code == 200:
            return InterbankResult(CONFIRMED)
        if response.status_code == 422 and self._is_refusal(response):
            return InterbankResult(REJECTED)

        logger.warning(f"payout_key={payout_key} interbank inconclusive: status={response.status_code}")
        return InterbankResult(TIMEOUT)

    @staticmethod
    def _is_refusal(response) -> bool:
        try:
            return response.json().get("status") == "refused"
        except (ValueError, AttributeError):
            return False
