import requests

from constants import BANK_API_URL, BANK_TIMEOUT_SECONDS, INTERNAL_TOKEN
from errors import BankRefused, BankUnavailable


class BankConnector:
    def get_client_identity(self, client_token: str) -> dict:
        try:
            response = requests.get(
                f"{BANK_API_URL}/auth/me",
                headers={"Authorization": f"Bearer {client_token}", "INTERNAL-TOKEN": INTERNAL_TOKEN},
                timeout=BANK_TIMEOUT_SECONDS,
            )
        except requests.exceptions.RequestException as error:
            raise BankUnavailable() from error

        if response.status_code == 401:
            return None
        if response.status_code != 200:
            raise BankUnavailable()
        return response.json()

    def post_ledger_transaction(self, payload: dict, idempotency_key: str, forward_refusals: bool = False) -> dict:
        try:
            response = requests.post(
                f"{BANK_API_URL}/ledger/transactions",
                json=payload,
                headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": idempotency_key},
                timeout=BANK_TIMEOUT_SECONDS,
            )
            transaction = response.json()
        except (requests.exceptions.RequestException, ValueError) as error:
            raise BankUnavailable() from error

        if forward_refusals and response.status_code == 422 and self._is_error_body(transaction):
            raise BankRefused(transaction)
        if response.status_code not in (200, 201) or not transaction.get("transaction_key"):
            raise BankUnavailable()
        return transaction

    @staticmethod
    def _is_error_body(body) -> bool:
        return isinstance(body, dict) and all(body.get(field) for field in ("title", "description", "translation", "code"))
