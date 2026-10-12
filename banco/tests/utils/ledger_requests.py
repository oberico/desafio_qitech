from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator
from tests.utils.request_generator import RequestGenerator

REFERENCE_FIELD = {
    "settlement": "settles_transaction_key",
    "refund": "reverses_transaction_key",
    "reversal": "reverses_transaction_key",
}
TARGET_PARENT = {"settlement": "receipt", "refund": "receipt", "reversal": "payout"}


class LedgerRequests:
    def __init__(self, api: RequestGenerator, internal_token: str):
        self.api = api
        self.internal_token = internal_token

    def post_transaction(self, payload: dict, idempotency_key: str) -> tuple:
        headers = {"INTERNAL-TOKEN": self.internal_token, "Idempotency-Key": idempotency_key}
        return self.api.post("/ledger/transactions", payload, headers)

    def create_transaction(self, type: str) -> str:
        references = {}
        if type in REFERENCE_FIELD:
            references[REFERENCE_FIELD[type]] = self.create_transaction(TARGET_PARENT[type])
        payload = PayloadGenerator.create_ledger_transaction_payload(type=type, **references)
        status, response = self.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201, f"could not create the {type} of the scenario: {status} {response}"
        return response["transaction_key"]

    def list_receipts(self, params: dict = None, headers: dict = None) -> tuple:
        request_headers = {"INTERNAL-TOKEN": self.internal_token} if headers is None else headers
        return self.api.get("/internal/ledger/receipts", request_headers, params)
