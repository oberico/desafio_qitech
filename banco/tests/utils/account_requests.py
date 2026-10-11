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

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"} if token else None
