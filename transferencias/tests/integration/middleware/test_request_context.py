import re
from uuid import UUID

import pytest

from tests.utils.random_generator import RandomGenerator

REQUEST_ID_HEADER = "X-Request-ID"

ROUTES = {
    "health_check": ("GET", "/health_check", None, None),
    "not_found": ("GET", "/route-that-does-not-exist", None, None),
    "bad_request": ("POST", "/payments", {}, {"Idempotency-Key": RandomGenerator.uuid()}),
}

SAFE_IDS = {
    "simple": ("health_check", "client-req_123"),
    "64_characters": ("health_check", "a" * 64),
    "on_not_found": ("not_found", "trace-404"),
}

UNSAFE_IDS = {
    "with_space": "has space",
    "65_characters": "a" * 65,
}


def is_uuid_v4(value: str) -> bool:
    try:
        return UUID(value).version == 4 and str(UUID(value)) == value
    except (ValueError, TypeError):
        return False


def send(api, route: str, request_id: str = None) -> tuple:
    method, path, body, headers = ROUTES[route]
    headers = dict(headers or {})
    if request_id is not None:
        headers[REQUEST_ID_HEADER] = request_id
    return api.request_with_headers(method, path, body, headers or None)


class TestRequestContext:
    @pytest.mark.parametrize("route", ROUTES.keys())
    def test_generates_uuid_v4_when_header_is_missing(self, api, route):
        _, _, headers = send(api, route)
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    @pytest.mark.parametrize("route, sent", SAFE_IDS.values(), ids=SAFE_IDS.keys())
    def test_echoes_safe_header_unchanged(self, api, route, sent):
        _, _, headers = send(api, route, sent)
        assert headers[REQUEST_ID_HEADER] == sent

    @pytest.mark.parametrize("sent", UNSAFE_IDS.values(), ids=UNSAFE_IDS.keys())
    def test_discards_unsafe_header(self, api, sent):
        _, _, headers = send(api, "health_check", sent)
        assert headers[REQUEST_ID_HEADER] != sent
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_two_requests_without_header_get_different_ids(self, api):
        _, _, first = send(api, "health_check")
        _, _, second = send(api, "health_check")
        assert first[REQUEST_ID_HEADER] != second[REQUEST_ID_HEADER]
