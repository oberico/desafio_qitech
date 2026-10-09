from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    @staticmethod
    def create_client_payload(**overrides) -> dict:
        payload = {"cpf": RandomGenerator.cpf()}
        payload.update(overrides)
        return payload
