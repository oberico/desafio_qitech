from tests.utils.request_generator import RequestGenerator


class InFlightRequests:
    def __init__(self, api: RequestGenerator, internal_token: str):
        self.api = api
        self.internal_token = internal_token

    def get_in_flight(self, account_key: str, internal_token: str = None) -> tuple:
        token = self.internal_token if internal_token is None else internal_token
        headers = {"INTERNAL-TOKEN": token} if token else None
        return self.api.get(f"/internal/accounts/{account_key}/in-flight", headers)
