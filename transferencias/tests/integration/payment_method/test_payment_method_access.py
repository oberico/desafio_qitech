import pytest

ERROR_FIELDS = {"title", "description", "translation", "code"}
BODY = {"fee_bps": 1234, "release_window_hours": 7}

REFUSED_HEADERS = {
    "without_token": None,
    "wrong_token": {"INTERNAL-TOKEN": "wrong-token"},
    "client_token": {"Authorization": "Bearer some-client-token"},
}


class TestPaymentMethodAccess:
    @pytest.mark.parametrize("headers", REFUSED_HEADERS.values(), ids=REFUSED_HEADERS.keys())
    def test_refuses_without_the_internal_token(self, payment_methods, headers):
        status, response = payment_methods.put_raw("pix", BODY, headers)
        assert status == 403
        assert response["code"] == "RNV000002"
        assert set(response.keys()) == ERROR_FIELDS
