from tests.utils.request_generator import RequestGenerator


class ClientRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def post_client(self, payload: dict) -> tuple:
        return self.api.post("/clients", payload)

    def get_me(self, token: str = None) -> tuple:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self.api.get("/me", headers=headers)

    def get_auth_me(self, token: str = None, internal_token: str = None) -> tuple:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if internal_token:
            headers["INTERNAL-TOKEN"] = internal_token
        return self.api.get("/auth/me", headers=headers)
