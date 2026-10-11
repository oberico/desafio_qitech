import pytest

from tests.utils.random_generator import RandomGenerator

PROTECTED_ROUTES = {
    "get_me": ("GET", "/me", None),
    "post_companies": ("POST", "/companies", {}),
    "get_company": ("GET", f"/companies/{RandomGenerator.uuid()}", None),
}


class TestClientAuth:
    @pytest.mark.parametrize("method, path, body", PROTECTED_ROUTES.values(), ids=PROTECTED_ROUTES.keys())
    @pytest.mark.parametrize("scheme_and_token", [None, "Bearer token-que-nao-existe", "Bearer INTERNAL"], ids=["missing_token", "unknown_token", "internal_token"])
    def test_refuses_request_without_a_valid_client_token(self, api, internal_token, method, path, body, scheme_and_token):
        headers = {"Authorization": scheme_and_token.replace("INTERNAL", internal_token)} if scheme_and_token else None
        status, response = api.request_with_headers(method, path, body, headers)[:2]
        assert status == 401
        assert response["code"] == "RNV000003"

    @pytest.mark.parametrize("method, path, body", PROTECTED_ROUTES.values(), ids=PROTECTED_ROUTES.keys())
    def test_refuses_valid_token_without_the_bearer_scheme(self, api, client_token, method, path, body):
        status, response = api.request_with_headers(method, path, body, {"Authorization": client_token})[:2]
        assert status == 401
        assert response["code"] == "RNV000003"
