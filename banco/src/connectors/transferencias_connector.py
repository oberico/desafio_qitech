import requests

from constants import INTERNAL_TOKEN, TRANSFERENCIAS_API_URL, TRANSFERENCIAS_TIMEOUT_SECONDS
from errors import ServiceBusy

IN_FLIGHT_FIELDS = ("held_payments", "pending_payouts")


class TransferenciasConnector:
    def count_in_flight(self, account_key: str) -> dict:
        try:
            response = requests.get(
                f"{TRANSFERENCIAS_API_URL}/internal/accounts/{account_key}/in-flight",
                headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
                timeout=TRANSFERENCIAS_TIMEOUT_SECONDS,
            )
            summary = response.json()
        except (requests.exceptions.RequestException, ValueError) as error:
            raise ServiceBusy() from error

        if response.status_code != 200 or not self._is_valid(summary):
            raise ServiceBusy()
        return summary

    @staticmethod
    def _is_valid(summary) -> bool:
        return isinstance(summary, dict) and all(
            isinstance(summary.get(field), int) and not isinstance(summary.get(field), bool) for field in IN_FLIGHT_FIELDS
        )
