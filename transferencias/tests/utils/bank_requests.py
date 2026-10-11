from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class BankRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def create_client_token(self) -> str:
        status, response = self.api.post("/clients", PayloadGenerator.create_client_payload())
        assert status == 201, f"não deu para criar o cliente no Banco: {status} {response}"
        return response["token"]
