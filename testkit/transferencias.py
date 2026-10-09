from testkit.payload_generator import PayloadGenerator
from testkit.request_generator import RequestGenerator as HttpRequestGenerator


class PaymentRequests:
    def __init__(self, api: HttpRequestGenerator):
        self.api = api

    def post_payment(self, payload: dict, idempotency_key: str = None) -> tuple:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self.api.post("/payments", payload, headers)

    def get_payment(self, payment_key: str) -> tuple:
        return self.api.get(f"/payments/{payment_key}")


__all__ = ["PayloadGenerator", "PaymentRequests"]
