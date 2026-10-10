import pytest


class TestClientMe:
    @pytest.mark.parametrize("token", [None, "token-que-nao-existe"], ids=["missing_token", "unknown_token"])
    def test_refuses_missing_or_unknown_token(self, clients, token):
        status, response = clients.get_me(token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_refuses_internal_token_in_place_of_client_token(self, clients, internal_token):
        status, response = clients.get_me(internal_token)
        assert status == 401
        assert response["code"] == "RNV000003"

    def test_returns_token_owner_data(self, clients, created_client):
        payload, created = created_client
        status, response = clients.get_me(created["token"])
        assert status == 200
        assert response["client_key"] == created["client_key"]
        assert response["cpf"] == payload["cpf"]
        assert response["name"] == payload["name"]
        assert response["email"] == payload["email"]
        assert response["birthdate"] == payload["birthdate"]

    def test_each_token_sees_only_its_own_client(self, clients, created_client, client_token):
        _, created = created_client
        status, response = clients.get_me(client_token)
        assert status == 200
        assert response["client_key"] != created["client_key"]

    def test_response_does_not_expose_internal_fields(self, clients, client_token):
        status, response = clients.get_me(client_token)
        assert status == 200
        assert "id" not in response
        assert "token" not in response
        assert "token_hash" not in response
