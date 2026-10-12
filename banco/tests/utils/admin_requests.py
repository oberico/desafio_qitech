from tests.utils.request_generator import RequestGenerator


class AdminRequests:
    def __init__(self, api: RequestGenerator):
        self.api = api

    def get(self, path: str, token: str = None, params: dict = None) -> tuple:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self.api.get(path, headers=headers, params=params)
