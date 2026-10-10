from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    @staticmethod
    def create_client_payload(**overrides) -> dict:
        payload = {"cpf": RandomGenerator.cpf()}
        payload.update(overrides)
        return payload

    @staticmethod
    def create_ledger_transaction_payload(**overrides) -> dict:
        payload = {
            "type": "receipt",
            "idempotency_key": RandomGenerator.uuid(),
            "entries": [
                {"account_code": "reserves", "debit_minor": 10000},
                {"account_code": "in_transit", "credit_minor": 10000},
            ],
        }
        payload.update(overrides)
        return payload 
