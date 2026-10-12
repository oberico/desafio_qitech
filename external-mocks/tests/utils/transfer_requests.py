import uuid

from tests.utils.request_generator import RequestGenerator


class TransferRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def post_transfer(self, payload: dict) -> tuple:
        return self.api.post("/interbank/transfers", payload)

    @staticmethod
    def build_payload(scenario: str = None, payout_key: str = None, amount_minor: int = 10000) -> dict:
        destination = {"bank": "001", "branch": "0001", "account": "12345-6"}
        if scenario is not None:
            destination["scenario"] = scenario
        return {
            "payout_key": payout_key or str(uuid.uuid4()),
            "amount_minor": amount_minor,
            "purpose": "payout",
            "destination": destination,
        }
