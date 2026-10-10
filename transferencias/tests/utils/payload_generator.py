from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    @staticmethod
    def create_payment_payload(**overrides) -> dict:
        payload = {
            "amount_minor": RandomGenerator.amount_minor(),
            "method": "pix",
            "company_key": RandomGenerator.uuid(),
            "account_key": RandomGenerator.uuid(),
        }
        payload.update(overrides)
        return payload
