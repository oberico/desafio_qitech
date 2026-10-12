import pytest

VALID = {"fee_bps": 1234, "release_window_hours": 7}

INVALID_BODIES = {
    "fee_negative": ({**VALID, "fee_bps": -1}, "RNV000010"),
    "fee_above_limit": ({**VALID, "fee_bps": 10001}, "RNV000010"),
    "window_negative": ({**VALID, "release_window_hours": -1}, "RNV000010"),
    "window_above_limit": ({**VALID, "release_window_hours": 8761}, "RNV000010"),
    "fee_float": ({**VALID, "fee_bps": 12.5}, "RNV000009"),
    "fee_integral_float": ({**VALID, "fee_bps": 12.0}, "RNV000009"),
    "window_float": ({**VALID, "release_window_hours": 7.5}, "RNV000009"),
    "fee_string": ({**VALID, "fee_bps": "12"}, "RNV000009"),
    "window_string": ({**VALID, "release_window_hours": "7"}, "RNV000009"),
    "fee_bool": ({**VALID, "fee_bps": True}, "RNV000009"),
    "window_bool": ({**VALID, "release_window_hours": False}, "RNV000009"),
    "fee_null": ({**VALID, "fee_bps": None}, "RNV000009"),
    "missing_fee": ({"release_window_hours": 7}, "RNV000007"),
    "missing_window": ({"fee_bps": 1234}, "RNV000007"),
    "extra_field": ({**VALID, "enumerator": "pix"}, "RNV000008"),
    "empty_body": ({}, "RNV000007"),
    "null_body": (None, "RNV000001"),
    "list_body": ([], "RNV000001"),
}


class TestPaymentMethodValidation:
    @pytest.mark.parametrize("body, code", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_rejects_an_invalid_body(self, payment_methods, body, code):
        status, response = payment_methods.put_authorized("pix", body)
        assert status == 400
        assert response["code"] == code

    @pytest.mark.parametrize("method", ["cash", "PIX", "Pix", "0", "unknown"])
    def test_rejects_a_method_outside_the_enum(self, payment_methods, method):
        status, response = payment_methods.put_authorized(method, VALID)
        assert status == 400
        assert response["code"] == "RNV000009"


    def test_range_translation_states_the_limit(self, payment_methods):
        _, response = payment_methods.put_authorized("pix", {**VALID, "fee_bps": 10001})
        assert response["title"] == "Value Out of Range"
        assert response["translation"] == "O campo fee_bps está fora do limite: deve ser no máximo 10000."

    def test_type_translation_states_the_expected_type(self, payment_methods):
        _, response = payment_methods.put_authorized("pix", {**VALID, "fee_bps": "12"})
        assert response["translation"] == "O campo fee_bps tem tipo ou formato inválido: esperado um número inteiro."

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
