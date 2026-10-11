from tests.utils.request_generator import RequestGenerator


class CompanyRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def post_company(self, payload: dict, token: str = None) -> tuple:
        return self.api.post("/companies", payload, self._auth(token))

    def get_company(self, company_key: str, token: str = None) -> tuple:
        return self.api.get(f"/companies/{company_key}", self._auth(token))

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"} if token else None
