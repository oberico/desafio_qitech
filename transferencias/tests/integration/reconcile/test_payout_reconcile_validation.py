import pytest

from tests.integration.reconcile.conftest import now

INVALID_BODIES = {
    "without_timezone": {"as_of": "2026-10-12T12:00:00"},
    "date_only": {"as_of": "2026-10-12"},
    "plain_text": {"as_of": "tomorrow"},
    "number": {"as_of": 1760000000},
    "null": {"as_of": None},
    "extra_field": {"as_of": "2026-10-12T12:00:00Z", "dry_run": True},
    "unknown_field_only": {"dry_run": True},
    "impossible_calendar_date": {"as_of": "2026-13-45T12:00:00Z"},
}


class TestPayoutReconcileValidation:
    @pytest.mark.parametrize("body", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_rejects_invalid_as_of(self, reconcile, internal_token, body):
        status, response = reconcile.run_raw(body, {"INTERNAL-TOKEN": internal_token})
        assert status == 400
        assert response["code"] == "RNV000001"

    @pytest.mark.parametrize("zone", ["Z", "-03:00", "+00:00"])
    def test_accepts_as_of_with_timezone(self, reconcile, zone):
        as_of = now().strftime("%Y-%m-%dT%H:%M:%S") + zone
        status, response = reconcile.run(as_of)
        assert status == 200
        assert set(response.keys()) == {"as_of", "settled", "failed", "pending"}

    def test_empty_body_uses_the_server_clock(self, reconcile):
        status, response = reconcile.run()
        assert status == 200
        assert response["as_of"]
        assert isinstance(response["settled"], list)
        assert isinstance(response["failed"], list)
        assert isinstance(response["pending"], list)
