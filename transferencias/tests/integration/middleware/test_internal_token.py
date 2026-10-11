import os

import pytest

from tests.utils.random_generator import RandomGenerator

INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "internal-token-dev")
ERROR_FIELDS = {"title", "description", "translation", "code"}

REFUSED_REQUESTS = {
    "get_without_token": ("GET", None, None),
    "get_with_wrong_token": ("GET", None, {"INTERNAL-TOKEN": "wrong-token"}),
}

PUBLIC_REQUESTS = {
    "health_check": ("GET", "/health_check", 204),
    "root": ("GET", "/", 200),
}


class TestInternalToken:
    @pytest.mark.parametrize("method, body, headers", REFUSED_REQUESTS.values(), ids=REFUSED_REQUESTS.keys())
    def test_refuses_internal_route(self, api, method, body, headers):
        status, response = api.request_with_headers(method, "/internal/anything", body, headers)[:2]
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refusal_has_exactly_the_four_error_fields(self, api):
        _, response = api.get("/internal/anything")
        assert set(response.keys()) == ERROR_FIELDS

    def test_internal_route_with_correct_token_passes_the_middleware(self, api):
        status, response = api.get("/internal/anything", {"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert status == 404
        assert response["code"] == "RNV000004"
        assert set(response.keys()) == ERROR_FIELDS

    @pytest.mark.parametrize("method, path, expected_status", PUBLIC_REQUESTS.values(), ids=PUBLIC_REQUESTS.keys())
    def test_public_routes_do_not_require_token(self, api, method, path, expected_status):
        status = api.request_with_headers(method, path)[0]
        assert status == expected_status

    def test_payments_route_does_not_require_internal_token(self, payments, payment_payload):
        status, _ = payments.post_payment(payment_payload(), RandomGenerator.uuid())
        assert status == 201
