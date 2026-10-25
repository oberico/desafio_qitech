import random

RESPONSE_FIELDS = {"version", "fee_bps", "created_at"}


def new_fee_bps() -> int:
    return random.randint(1000, 9000)


class TestPayoutFeeVersioning:
    def test_a_different_value_creates_a_new_version(self, changed_payout_fee):
        _, before = changed_payout_fee(new_fee_bps())
        fee_bps = before["fee_bps"] + 1

        status, response = changed_payout_fee(fee_bps)

        assert status == 201
        assert set(response) == RESPONSE_FIELDS
        assert response["fee_bps"] == fee_bps
        assert response["version"] == before["version"] + 1

    def test_the_same_value_answers_200_without_a_new_version(self, changed_payout_fee):
        _, created = changed_payout_fee(new_fee_bps())

        status, response = changed_payout_fee(created["fee_bps"])

        assert status == 200
        assert response["version"] == created["version"]
        assert response["fee_bps"] == created["fee_bps"]
        assert response["created_at"] == created["created_at"]

    def test_accepts_the_range_limits(self, changed_payout_fee):
        for fee_bps in (0, 10000):
            status, response = changed_payout_fee(fee_bps)
            assert status in (200, 201)
            assert response["fee_bps"] == fee_bps
