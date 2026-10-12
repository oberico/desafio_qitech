class TestHealthCheck:
    def test_health_check_returns_no_content(self, api):
        status, response = api.get("/health_check")
        assert status == 204
        assert response is None

    def test_root_returns_the_service_name(self, api):
        status, response = api.get("/")
        assert status == 200
        assert response == {"service": "banco"}
