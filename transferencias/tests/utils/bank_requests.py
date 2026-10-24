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

    def post_close(self, account_key: str, token: str) -> tuple:
        return self.api.post(f"/accounts/{account_key}/close", headers=self._auth(token))

    def block_account(self, account_key: str, internal_token: str) -> None:
        status, response = self.api.post(f"/internal/accounts/{account_key}/block", headers={"INTERNAL-TOKEN": internal_token})
        assert status == 200, f"não deu para bloquear a conta no Banco: {status} {response}"

    def unblock_account(self, account_key: str, internal_token: str) -> None:
        status, response = self.api.post(f"/internal/accounts/{account_key}/unblock", headers={"INTERNAL-TOKEN": internal_token})
        assert status == 200, f"não deu para desbloquear a conta no Banco: {status} {response}"

    def post_ledger_transaction(self, payload: dict, idempotency_key: str, internal_token: str) -> tuple:
        headers = {"INTERNAL-TOKEN": internal_token, "Idempotency-Key": idempotency_key}
        return self.api.post("/ledger/transactions", payload, headers)

    def get_balance_minor(self, account_key: str, token: str) -> int:
        status, response = self.api.get(f"/accounts/{account_key}/balance", self._auth(token))
        assert status == 200, f"não deu para ler o saldo no Banco: {status} {response}"
        return response["balance_minor"]

    def get_revenue_minor(self, admin_token: str) -> int:
        status, response = self.api.get("/admin/internal-accounts", self._auth(admin_token))
        assert status == 200, f"não deu para ler as contas internas no Banco: {status} {response}"
        return response["revenue_minor"]

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}
