class TestHealthCheck:
    def test_health_check_returns_no_content(self, api):
        status, response = api.get("/health_check")
        assert status == 204
        assert response is None

    def test_root_returns_the_service_name(self, api):
        status, response = api.get("/")
        assert status == 200
        assert response == {"service": "external-mocks"}

    def test_unknown_route_returns_not_found(self, api):
        status, response = api.get("/nowhere")
        assert status == 404
        assert response["code"] == "RNV000004"

    def test_wrong_method_returns_method_not_allowed(self, api):
        status, response = api.get("/interbank/transfers")
        assert status == 405
        assert response["code"] == "RNV000005"
