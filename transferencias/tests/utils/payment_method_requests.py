from tests.utils.request_generator import RequestGenerator


class PaymentMethodRequests:
    def __init__(self, api: RequestGenerator, internal_token: str):
        self.api = api
        self.internal_token = internal_token

    def put(self, method: str, fee_bps, release_window_hours) -> tuple:
        body = {"fee_bps": fee_bps, "release_window_hours": release_window_hours}
        return self.api.put(f"/internal/payment-methods/{method}", body, self._auth())

    def put_raw(self, method: str, body, headers: dict = None) -> tuple:
        return self.api.put(f"/internal/payment-methods/{method}", body, headers)

    def put_authorized(self, method: str, body) -> tuple:
        return self.api.put(f"/internal/payment-methods/{method}", body, self._auth())

    def _auth(self) -> dict:
        return {"INTERNAL-TOKEN": self.internal_token}
