from tests.utils.request_generator import RequestGenerator

JOB_TIMEOUT_SECONDS = 300


class ReconcileRequests:
    def __init__(self, base_url: str, internal_token: str):
        self.api = RequestGenerator(base_url, timeout=JOB_TIMEOUT_SECONDS)
        self.internal_token = internal_token

    def run(self, as_of: str = None) -> tuple:
        body = {"as_of": as_of} if as_of is not None else None
        return self.api.post("/internal/payouts/reconcile", body, {"INTERNAL-TOKEN": self.internal_token})

    def run_raw(self, body, headers: dict = None) -> tuple:
        return self.api.post("/internal/payouts/reconcile", body, headers)
