import pytest

ERROR_FIELDS = {"title", "description", "translation", "code"}

INVALID_BODIES = {
    "not_an_object": ([1, 2], "RNV000001"),
    "missing_fee_bps": ({}, "RNV000007"),
    "extra_field": ({"fee_bps": 50, "release_window_hours": 1}, "RNV000008"),
    "fee_bps_as_text": ({"fee_bps": "50"}, "RNV000009"),
    "fee_bps_decimal": ({"fee_bps": 50.5}, "RNV000009"),
    "fee_bps_boolean": ({"fee_bps": True}, "RNV000009"),
    "fee_bps_negative": ({"fee_bps": -1}, "RNV000010"),
    "fee_bps_above_10000": ({"fee_bps": 10001}, "RNV000010"),
}


class TestPayoutFeeValidation:
    @pytest.mark.parametrize("body, code", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_refuses_an_invalid_body(self, payout_fees, body, code):
        status, response = payout_fees.put_authorized(body)
        assert status == 400
        assert response["code"] == code
        assert set(response) == ERROR_FIELDS
