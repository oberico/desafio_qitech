from uuid import uuid4

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPayoutGet:
    def test_gets_created_payout_by_key(self, payouts, payout_payload):
        _, created = payouts.post_payout(payout_payload(), str(uuid4()))

        status, response = payouts.get_payout(created["payout_key"])

        assert status == 200
        assert response == created

    def test_get_unknown_payout_is_not_found(self, payouts):
        status, response = payouts.get_payout(str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001032"
        assert set(response) == ERROR_FIELDS

    def test_get_malformed_key_is_not_found(self, payouts):
        status, response = payouts.get_payout("not-a-key")
        assert status == 404
        assert response["code"] == "RNV001032"

    def test_payout_of_another_client_is_not_found(self, payouts, other_payouts, payout_payload):
        _, created = payouts.post_payout(payout_payload(), str(uuid4()))

        status, response = other_payouts.get_payout(created["payout_key"])

        assert status == 404
        assert response["code"] == "RNV001032"

    def test_get_works_while_the_account_is_blocked(self, payouts, payout_payload, bank, internal_token):
        _, created = payouts.post_payout(payout_payload(), str(uuid4()))
        bank.block_account(created["account_key"], internal_token)

        status, response = payouts.get_payout(created["payout_key"])

        assert status == 200
        assert response["payout_key"] == created["payout_key"]
