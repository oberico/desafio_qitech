import pytest

VALID = {"fee_bps": 1234, "release_window_hours": 7}

INVALID_BODIES = {
    "fee_negative": {**VALID, "fee_bps": -1},
    "fee_above_limit": {**VALID, "fee_bps": 10001},
    "window_negative": {**VALID, "release_window_hours": -1},
    "window_above_limit": {**VALID, "release_window_hours": 8761},
    "fee_float": {**VALID, "fee_bps": 12.5},
    "fee_integral_float": {**VALID, "fee_bps": 12.0},
    "window_float": {**VALID, "release_window_hours": 7.5},
    "fee_string": {**VALID, "fee_bps": "12"},
    "window_string": {**VALID, "release_window_hours": "7"},
    "fee_bool": {**VALID, "fee_bps": True},
    "window_bool": {**VALID, "release_window_hours": False},
    "fee_null": {**VALID, "fee_bps": None},
    "missing_fee": {"release_window_hours": 7},
    "missing_window": {"fee_bps": 1234},
    "extra_field": {**VALID, "enumerator": "pix"},
    "empty_body": {},
    "null_body": None,
    "list_body": [],
}


class TestPaymentMethodValidation:
    @pytest.mark.parametrize("body", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_rejects_an_invalid_body(self, payment_methods, body):
        status, response = payment_methods.put_authorized("pix", body)
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("method", ["cash", "PIX", "Pix", "0", "unknown"])
    def test_rejects_a_method_outside_the_enum(self, payment_methods, method):
        status, response = payment_methods.put_authorized(method, VALID)
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_unknown_method_error_points_to_the_method(self, payment_methods):
        status, response = payment_methods.put_authorized("ted", VALID)
        assert status == 400
        assert "method: " in response["description"]
        assert "body" not in response["description"]

    @pytest.mark.parametrize("fee_bps, window", [(0, 0), (10000, 8760)])
    def test_accepts_the_limits(self, changed_method, fee_bps, window):
        status, response = changed_method("card", fee_bps, window)
        assert response["fee_bps"] == fee_bps
        assert response["release_window_hours"] == window
