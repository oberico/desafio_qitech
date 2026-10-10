import re
from uuid import UUID

REQUEST_ID_HEADER = "X-Request-ID"
SAFE_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


def is_uuid_v4(value: str) -> bool:
    try:
        return UUID(value).version == 4 and str(UUID(value)) == value
    except (ValueError, TypeError):
        return False


class TestRequestContext:
    def test_generates_uuid_v4_when_header_is_missing(self, api):
        _, _, headers = api.request_with_headers("GET", "/health_check")
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_echoes_safe_header_unchanged(self, api):
        _, _, headers = api.request_with_headers("GET", "/health_check", headers={REQUEST_ID_HEADER: "client-req_123"})
        assert headers[REQUEST_ID_HEADER] == "client-req_123"

    def test_discards_header_with_space(self, api):
        sent = "has space"
        _, _, headers = api.request_with_headers("GET", "/health_check", headers={REQUEST_ID_HEADER: sent})
        assert headers[REQUEST_ID_HEADER] != sent
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_discards_header_with_semicolon(self, api):
        sent = "abc;def"
        _, _, headers = api.request_with_headers("GET", "/health_check", headers={REQUEST_ID_HEADER: sent})
        assert headers[REQUEST_ID_HEADER] != sent
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_discards_header_with_65_characters(self, api):
        sent = "a" * 65
        _, _, headers = api.request_with_headers("GET", "/health_check", headers={REQUEST_ID_HEADER: sent})
        assert headers[REQUEST_ID_HEADER] != sent
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_accepts_header_with_64_characters(self, api):
        sent = "a" * 64
        _, _, headers = api.request_with_headers("GET", "/health_check", headers={REQUEST_ID_HEADER: sent})
        assert headers[REQUEST_ID_HEADER] == sent

    def test_returns_header_on_root(self, api):
        _, _, headers = api.request_with_headers("GET", "/")
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_returns_header_on_health_check(self, api):
        _, _, headers = api.request_with_headers("GET", "/health_check")
        assert REQUEST_ID_HEADER in headers

    def test_returns_header_on_not_found(self, api):
        status, _, headers = api.request_with_headers("GET", "/route-that-does-not-exist")
        assert status == 404
        assert is_uuid_v4(headers[REQUEST_ID_HEADER])

    def test_echoes_safe_header_on_not_found(self, api):
        _, _, headers = api.request_with_headers("GET", "/route-that-does-not-exist", headers={REQUEST_ID_HEADER: "trace-404"})
        assert headers[REQUEST_ID_HEADER] == "trace-404"

    def test_two_requests_without_header_get_different_ids(self, api):
        _, _, first = api.request_with_headers("GET", "/health_check")
        _, _, second = api.request_with_headers("GET", "/health_check")
        assert first[REQUEST_ID_HEADER] != second[REQUEST_ID_HEADER]
