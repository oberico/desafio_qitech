import pytest

REFUSED_HEADERS = {
    "without_token": None,
    "wrong_token": {"INTERNAL-TOKEN": "wrong-token"},
    "client_token": {"Authorization": "Bearer some-client-token"},
}

INVALID_BODIES = {
    "without_timezone": ({"as_of": "2026-10-12T12:00:00"}, "RNV000009"),
    "plain_text": ({"as_of": "tomorrow"}, "RNV000009"),
    "extra_field": ({"as_of": "2026-10-12T12:00:00Z", "dry_run": True}, "RNV000008"),
}


class TestReceiptReconcileAccess:
    @pytest.mark.parametrize("headers", REFUSED_HEADERS.values(), ids=REFUSED_HEADERS.keys())
    def test_refuses_without_the_internal_token(self, receipt_reconcile, headers):
        status, response = receipt_reconcile.run_raw(None, headers)
        assert status == 403
        assert response["code"] == "RNV000002"

    @pytest.mark.parametrize("body, code", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_rejects_an_invalid_body(self, receipt_reconcile, internal_token, body, code):
        status, response = receipt_reconcile.run_raw(body, {"INTERNAL-TOKEN": internal_token})
        assert status == 400
        assert response["code"] == code
