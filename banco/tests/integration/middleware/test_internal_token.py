import os

INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "internal-token-dev")
ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestInternalToken:
    def test_refuses_internal_route_without_token(self, api):
        status, response = api.get("/internal/anything")
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refuses_internal_route_with_wrong_token(self, api):
        status, response = api.get("/internal/anything", {"INTERNAL-TOKEN": "wrong-token"})
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refuses_internal_post_without_token(self, api):
        status, response = api.post("/internal/anything", {})
        assert status == 403
        assert response["code"] == "RNV000002"

    def test_refusal_has_exactly_the_four_error_fields(self, api):
        _, response = api.get("/internal/anything")
        assert set(response.keys()) == ERROR_FIELDS

    def test_internal_route_with_correct_token_passes_the_middleware(self, api):
        status, _ = api.get("/internal/anything", {"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert status == 404

    def test_health_check_does_not_require_token(self, api):
        status, _ = api.get("/health_check")
        assert status == 204

    def test_root_does_not_require_token(self, api):
        status, _ = api.get("/")
        assert status == 200
