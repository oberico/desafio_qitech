import requests

from constants import BANK_API_URL, BANK_TIMEOUT_SECONDS, INTERNAL_TOKEN
from errors import BankUnavailable


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
