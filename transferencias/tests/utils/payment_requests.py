from tests.utils.request_generator import RequestGenerator


class PaymentRequests:
    def __init__(self, api: RequestGenerator, client_token: str):
        self.api = api
        self.client_token = client_token

    def post_payment(self, payload: dict, idempotency_key: str = None) -> tuple:
        headers = self._auth()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return self.api.post("/payments", payload, headers)

    def get_payment(self, payment_key: str) -> tuple:
        return self.api.get(f"/payments/{payment_key}", self._auth())

    def list_payments(self, params: dict = None) -> tuple:
        return self.api.get("/payments", self._auth(), params)

    def refund_payment(self, payment_key: str) -> tuple:
        return self.api.post(f"/payments/{payment_key}/refund", None, self._auth())

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.client_token}"}
