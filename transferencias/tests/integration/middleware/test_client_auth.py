import pytest

from tests.utils.random_generator import RandomGenerator

ERROR_FIELDS = {"title", "description", "translation", "code"}

PROTECTED_ROUTES = {
    "post_payments": ("POST", "/payments", {}),
    "get_payment": ("GET", f"/payments/{RandomGenerator.uuid()}", None),
    "refund_payment": ("POST", f"/payments/{RandomGenerator.uuid()}/refund", None),
}

INVALID_AUTHORIZATIONS = {
    "missing_token": None,
    "unknown_token": "Bearer token-que-nao-existe",
    "internal_token_as_client_token": "Bearer INTERNAL",
}


class TestClientAuth:
    @pytest.mark.parametrize("method, path, body", PROTECTED_ROUTES.values(), ids=PROTECTED_ROUTES.keys())
    @pytest.mark.parametrize("authorization", INVALID_AUTHORIZATIONS.values(), ids=INVALID_AUTHORIZATIONS.keys())
    def test_refuses_request_without_a_valid_client_token(self, api, internal_token, method, path, body, authorization):
        headers = {"Authorization": authorization.replace("INTERNAL", internal_token)} if authorization else None
        status, response = api.request_with_headers(method, path, body, headers)[:2]
        assert status == 401
        assert response["code"] == "RNV000003"

    @pytest.mark.parametrize("method, path, body", PROTECTED_ROUTES.values(), ids=PROTECTED_ROUTES.keys())
    def test_refuses_valid_token_without_the_bearer_scheme(self, api, client_token, method, path, body):
        status, response = api.request_with_headers(method, path, body, {"Authorization": client_token})[:2]
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_refusal_has_exactly_the_four_error_fields(self, api):
        status, response = api.request_with_headers("GET", f"/payments/{RandomGenerator.uuid()}")[:2]
        assert status == 401
        assert set(response.keys()) == ERROR_FIELDS

    def test_accepts_a_valid_client_token(self, api, client_token):
        status, response = api.request_with_headers("GET", f"/payments/{RandomGenerator.uuid()}", None, {"Authorization": f"Bearer {client_token}"})[:2]
        assert status == 404
        assert response["code"] == "RNV001025"
