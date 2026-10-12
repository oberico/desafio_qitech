import pytest

INVALID_BODIES = {
    "without_timezone": ({"as_of": "2026-10-12T12:00:00"}, "RNV000009"),
    "date_only": ({"as_of": "2026-10-12"}, "RNV000009"),
    "plain_text": ({"as_of": "tomorrow"}, "RNV000009"),
    "number": ({"as_of": 1760000000}, "RNV000009"),
    "null": ({"as_of": None}, "RNV000009"),
    "extra_field": ({"as_of": "2026-10-12T12:00:00Z", "dry_run": True}, "RNV000008"),
    "unknown_field_only": ({"dry_run": True}, "RNV000008"),
    "impossible_calendar_date": ({"as_of": "2026-13-45T12:00:00Z"}, "RNV000009"),
}


class TestSettlementValidation:
    @pytest.mark.parametrize("body, code", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
    def test_rejects_invalid_as_of(self, settlements, internal_token, body, code):
        status, response = settlements.run_raw(body, {"INTERNAL-TOKEN": internal_token})
        assert status == 400
        assert response["code"] == code

    @pytest.mark.parametrize("as_of", ["2026-10-12T12:00:00Z", "2026-10-12T12:00:00-03:00", "2026-10-12T12:00:00.123+00:00"])
    def test_accepts_as_of_with_timezone(self, settlements, as_of):
        status, response = settlements.run(as_of)
        assert status == 200
        assert set(response.keys()) == {"as_of", "settled", "deferred"}

    def test_empty_body_uses_the_server_clock(self, settlements):
        status, response = settlements.run()
        assert status == 200
        assert response["as_of"]
        assert isinstance(response["settled"], list)
        assert isinstance(response["deferred"], list)
