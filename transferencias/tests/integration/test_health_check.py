class TestHealthCheck:
    def test_health_check_returns_ok(self, api):
        status, response = api.get("/health_check")
        assert status == 204

    def test_root_returns_ok(self, api):
        status, response = api.get("/")
        assert status == 200
