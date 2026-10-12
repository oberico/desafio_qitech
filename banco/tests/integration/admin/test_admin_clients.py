import pytest

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

ROUTE = "/admin/clients"
PAGE_FIELDS = {"data", "limit", "cursor", "is_last_page"}
CLIENT_FIELDS = {"client_key", "name", "created_at"}


def create_clients(clients, amount: int) -> list:
    created_keys = []
    for _ in range(amount):
        status, response = clients.post_client(PayloadGenerator.create_client_payload())
        assert status == 201, f"não deu para criar o cliente do cenário: {status} {response}"
        created_keys.append(response["client_key"])
    return created_keys


class TestAdminClients:
    def test_returns_a_page(self, admin, admin_token, created_client):
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert set(response) == PAGE_FIELDS

    def test_newest_client_comes_first(self, admin, admin_token, created_client):
        _, created = created_client
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert response["data"][0]["client_key"] == created["client_key"]

    def test_lists_only_public_client_fields(self, admin, admin_token, created_client):
        payload, created = created_client
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        first = response["data"][0]
        assert set(first) == CLIENT_FIELDS
        assert first["name"] == payload["name"]
        assert first["created_at"]

    def test_default_page_size_is_twenty(self, admin, admin_token, clients):
        create_clients(clients, 21)
        status, response = admin.get(ROUTE, admin_token)
        assert status == 200
        assert len(response["data"]) == 20
        assert response["is_last_page"] is False

    def test_limit_sets_the_page_size(self, admin, admin_token, clients):
        create_clients(clients, 3)
        status, response = admin.get(ROUTE, admin_token, {"limit": 2})
        assert status == 200
        assert len(response["data"]) == 2

    def test_page_that_is_not_the_last_has_cursor(self, admin, admin_token, clients):
        create_clients(clients, 2)
        status, response = admin.get(ROUTE, admin_token, {"limit": 1})
        assert status == 200
        assert response["is_last_page"] is False
        assert response["cursor"]
        assert response["cursor"] != response["data"][-1]["client_key"]

    def test_envelope_echoes_the_limit(self, admin, admin_token, clients):
        create_clients(clients, 2)
        status, response = admin.get(ROUTE, admin_token, {"limit": 2})
        assert status == 200
        assert response["limit"] == 2

    def test_cursor_walks_the_pages_without_repeating_or_skipping(self, admin, admin_token, clients):
        created_keys = create_clients(clients, 3)

        seen = []
        params = {"limit": 1}
        for _ in range(3):
            status, response = admin.get(ROUTE, admin_token, params)
            assert status == 200
            seen.extend(client["client_key"] for client in response["data"])
            params = {"limit": 1, "cursor": response["cursor"]}

        assert seen == list(reversed(created_keys))

    @pytest.mark.parametrize("limit", ["0", "101", "-1", "dez", "1.5"])
    def test_refuses_invalid_limit(self, admin, admin_token, limit):
        status, response = admin.get(ROUTE, admin_token, {"limit": limit})
        assert status == 400
        assert response["code"] == "RNV000009"

    @pytest.mark.parametrize("cursor", [RandomGenerator.uuid(), "cursor-inventado", ""], ids=["public_key", "made_up", "empty"])
    def test_refuses_invalid_cursor(self, admin, admin_token, cursor):
        status, response = admin.get(ROUTE, admin_token, {"cursor": cursor})
        assert status == 400
        assert response["code"] == "RNV000011"

    def test_refuses_tampered_cursor(self, admin, admin_token, clients):
        create_clients(clients, 2)
        _, first_page = admin.get(ROUTE, admin_token, {"limit": 1})
        cursor = first_page["cursor"]
        tampered = ("B" if cursor[0] == "A" else "A") + cursor[1:]
        status, response = admin.get(ROUTE, admin_token, {"limit": 1, "cursor": tampered})
        assert status == 400
        assert response["code"] == "RNV000011"

    def test_refuses_unknown_query_parameter(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token, {"pagina": 2})
        assert status == 400
        assert response["code"] == "RNV000008"

    def test_unknown_parameter_error_points_to_the_query(self, admin, admin_token):
        status, response = admin.get(ROUTE, admin_token, {"pagina": 2})
        assert status == 400
        assert "query: " in response["description"]
        assert "body" not in response["description"]
