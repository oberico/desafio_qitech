import pytest

ADMIN_ROUTES = ["/admin/clients", "/admin/companies", "/admin/accounts", "/admin/internal-accounts"]


class TestAdminAccess:
    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_token(self, admin, route, token):
        status, response = admin.get(route, token)
        assert status == 401
        assert response["code"] == "RNV000003"

    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_refuses_client_token(self, admin, client_token, route):
        status, response = admin.get(route, client_token)
        assert status == 403
        assert response["code"] == "RNV001027"

    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_refuses_internal_token_in_place_of_admin_token(self, admin, internal_token, route):
        status, response = admin.get(route, internal_token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_admin_token_passes_to_the_routing_layer(self, admin, admin_token):
        status, response = admin.get("/admin/route-that-does-not-exist", admin_token)
        assert status == 404
        assert response["code"] == "RNV000004"
