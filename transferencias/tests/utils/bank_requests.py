from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class BankRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def create_client_token(self) -> str:
        status, response = self.api.post("/clients", PayloadGenerator.create_client_payload())
        assert status == 201, f"não deu para criar o cliente no Banco: {status} {response}"
        return response["token"]

    def create_company(self, token: str, cnpj: str = None) -> str:
        payload = PayloadGenerator.create_company_payload(**({"cnpj": cnpj} if cnpj else {}))
        status, response = self.api.post("/companies", payload, self._auth(token))
        assert status == 201, f"não deu para criar a empresa no Banco: {status} {response}"
        return response["company_key"]

    def open_account(self, company_key: str, token: str) -> dict:
        status, response = self.api.post(f"/companies/{company_key}/accounts", headers=self._auth(token))
        assert status == 201, f"não deu para abrir a conta no Banco: {status} {response}"
        return response

    def close_account(self, account_key: str, token: str) -> None:
        status, response = self.api.post(f"/accounts/{account_key}/close", headers=self._auth(token))
        assert status == 200, f"não deu para encerrar a conta no Banco: {status} {response}"

    def post_ledger_transaction(self, payload: dict, idempotency_key: str, internal_token: str) -> tuple:
        headers = {"INTERNAL-TOKEN": internal_token, "Idempotency-Key": idempotency_key}
        return self.api.post("/ledger/transactions", payload, headers)

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}
