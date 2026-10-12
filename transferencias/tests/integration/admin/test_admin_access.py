import pytest

ROUTE = "/admin/payments"


class TestAdminAccess:
    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_token(self, admin, token):
        status, response = admin.get(ROUTE, token)

        assert status == 401
        assert response["code"] == "RNV000003"

    def test_refuses_client_token(self, admin, client_token):
        status, response = admin.get(ROUTE, client_token)

        assert status == 403
        assert response["code"] == "RNV001027"

    def test_refuses_internal_token_in_place_of_admin_token(self, admin, internal_token):
        status, response = admin.get(ROUTE, internal_token)

        assert status == 401
        assert response["code"] == "RNV000003"

    def test_admin_token_passes(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token)

        assert status == 200
        assert "data" in response

    def test_admin_token_passes_to_the_routing_layer(self, admin, admin_token):
        status, response = admin.get("/admin/route-that-does-not-exist", admin_token)

        assert status == 404
        assert response["code"] == "RNV000004"

    def test_client_token_does_not_reach_admin_route_through_client_middleware(self, api, client_token):
        status, response = api.get(ROUTE, {"Authorization": f"Bearer {client_token}"})

        assert status == 403
        assert response["code"] == "RNV001027"
