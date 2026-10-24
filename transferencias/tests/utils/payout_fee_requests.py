from tests.utils.request_generator import RequestGenerator


class PayoutFeeRequests:
    def __init__(self, api: RequestGenerator, internal_token: str):
        self.api = api
        self.internal_token = internal_token

    def put(self, fee_bps) -> tuple:
        return self.api.put("/internal/payout-fee", {"fee_bps": fee_bps}, self._auth())

    def put_raw(self, body, headers: dict = None) -> tuple:
        return self.api.put("/internal/payout-fee", body, headers)

    def put_authorized(self, body) -> tuple:
        return self.api.put("/internal/payout-fee", body, self._auth())

    def _auth(self) -> dict:
        return {"INTERNAL-TOKEN": self.internal_token}
