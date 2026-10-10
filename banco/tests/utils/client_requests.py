from tests.utils.request_generator import RequestGenerator


class ClientRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def post_client(self, payload: dict) -> tuple:
        return self.api.post("/clients", payload)

    def get_me(self, token: str = None) -> tuple:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self.api.get("/me", headers=headers)
