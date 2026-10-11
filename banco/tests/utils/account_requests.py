from tests.utils.request_generator import RequestGenerator


class AccountRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def post_account(self, company_key: str, token: str = None) -> tuple:
        return self.api.post(f"/companies/{company_key}/accounts", headers=self._auth(token))

    def get_account(self, account_key: str, token: str = None) -> tuple:
        return self.api.get(f"/accounts/{account_key}", headers=self._auth(token))

    def close(self, account_key: str, token: str = None) -> tuple:
        return self.api.post(f"/accounts/{account_key}/close", headers=self._auth(token))

    def block(self, account_key: str, internal_token: str = None) -> tuple:
        return self.api.post(f"/internal/accounts/{account_key}/block", headers=self._internal(internal_token))

    def unblock(self, account_key: str, internal_token: str = None) -> tuple:
        return self.api.post(f"/internal/accounts/{account_key}/unblock", headers=self._internal(internal_token))

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"} if token else None

    @staticmethod
    def _internal(internal_token: str) -> dict:
        return {"INTERNAL-TOKEN": internal_token} if internal_token else None
