from tests.utils.request_generator import RequestGenerator


class InternalAccountRequests:
    def __init__(self, api: RequestGenerator, internal_token: str):
        self.api = api
        self.internal_token = internal_token

    def list_internal_accounts(self) -> tuple:
        return self.api.get("/internal/internal-accounts", {"INTERNAL-TOKEN": self.internal_token})
