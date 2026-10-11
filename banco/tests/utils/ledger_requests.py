from tests.utils.request_generator import RequestGenerator

class LedgerRequests:
    def __init__(self, api: RequestGenerator, internal_token: str):
        self.api = api
        self.internal_token = internal_token

    def post_transaction(self, payload: dict, idempotency_key: str) -> tuple:
        headers = {"INTERNAL-TOKEN": self.internal_token, "Idempotency-Key": idempotency_key}
        return self.api.post("/ledger/transactions", payload, headers)