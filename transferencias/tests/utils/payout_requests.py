from tests.utils.request_generator import RequestGenerator


class PayoutRequests:
    def __init__(self, api: RequestGenerator, client_token: str):
        self.api = api
        self.client_token = client_token

    def post_payout(self, payload: dict, idempotency_key: str = None) -> tuple:
        headers = self._auth()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return self.api.post("/payouts", payload, headers)

    def get_payout(self, payout_key: str) -> tuple:
        return self.api.get(f"/payouts/{payout_key}", self._auth())

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.client_token}"}
