import pytest

ERROR_FIELDS = {"title", "description", "translation", "code"}

REFUSED_HEADERS = {
    "without_token": None,
    "wrong_token": {"INTERNAL-TOKEN": "wrong-token"},
    "client_token": {"Authorization": "Bearer some-client-token"},
}


class TestPayoutFeeAccess:
    @pytest.mark.parametrize("headers", REFUSED_HEADERS.values(), ids=REFUSED_HEADERS.keys())
    def test_refuses_without_the_internal_token(self, payout_fees, headers):
        status, response = payout_fees.put_raw({"fee_bps": 77}, headers)
        assert status == 403
        assert response["code"] == "RNV000002"
        assert set(response) == ERROR_FIELDS
