import copy
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from tests.utils.transfer_requests import TransferRequests

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestConfirm:
    @pytest.mark.parametrize("scenario", [None, "confirm"])
    def test_confirms_by_default_and_when_asked(self, transfers, scenario):
        status, response = transfers.post_transfer(TransferRequests.build_payload(scenario))
        assert status == 200
        assert response["status"] == "confirmed"
        assert str(uuid.UUID(response["transfer_id"], version=4)) == response["transfer_id"]

    def test_repeated_calls_return_the_same_transfer_id(self, transfers):
        payload = TransferRequests.build_payload("confirm")
        first_status, first = transfers.post_transfer(payload)
        second_status, second = transfers.post_transfer(payload)
        assert first_status == second_status == 200
        assert first["transfer_id"] == second["transfer_id"]

    def test_concurrent_calls_return_the_same_transfer_id(self, transfers):
        payload = TransferRequests.build_payload("confirm")
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: transfers.post_transfer(payload), range(10)))
        assert {status for status, _ in results} == {200}
        assert len({response["transfer_id"] for _, response in results}) == 1

    def test_different_payout_keys_get_different_transfer_ids(self, transfers):
        _, first = transfers.post_transfer(TransferRequests.build_payload())
        _, second = transfers.post_transfer(TransferRequests.build_payload())
        assert first["transfer_id"] != second["transfer_id"]


class TestRefuse:
    def test_refuses_definitively(self, transfers):
        status, response = transfers.post_transfer(TransferRequests.build_payload("refuse"))
        assert status == 422
        assert response == {"status": "refused", "reason": "destination_refused"}

    def test_refusal_is_repeated_on_retry(self, transfers):
        payload = TransferRequests.build_payload("refuse")
        first_status, _ = transfers.post_transfer(payload)
        second_status, second = transfers.post_transfer(payload)
        assert first_status == second_status == 422
        assert second["reason"] == "destination_refused"


class TestTimeout:
    def test_response_does_not_arrive_in_useful_time(self, impatient_transfers):
        with pytest.raises(requests.exceptions.ReadTimeout):
            impatient_transfers.post_transfer(TransferRequests.build_payload("timeout"))

    def test_keeps_stalling_on_every_call(self, impatient_transfers):
        payload = TransferRequests.build_payload("timeout")
        for _ in range(3):
            with pytest.raises(requests.exceptions.ReadTimeout):
                impatient_transfers.post_transfer(payload)


class TestFlaky:
    def test_first_two_calls_stall_and_third_confirms(self, transfers, impatient_transfers):
        payload = TransferRequests.build_payload("flaky")
        for _ in range(2):
            with pytest.raises(requests.exceptions.ReadTimeout):
                impatient_transfers.post_transfer(payload)
        status, response = transfers.post_transfer(payload)
        assert status == 200
        assert response["status"] == "confirmed"

    def test_calls_after_the_third_keep_confirming_with_the_same_transfer_id(self, transfers, impatient_transfers):
        payload = TransferRequests.build_payload("flaky")
        for _ in range(2):
            with pytest.raises(requests.exceptions.ReadTimeout):
                impatient_transfers.post_transfer(payload)
        _, third = transfers.post_transfer(payload)
        status, fourth = transfers.post_transfer(payload)
        assert status == 200
        assert fourth["transfer_id"] == third["transfer_id"]

    def test_each_payout_key_has_its_own_count(self, transfers, impatient_transfers):
        first = TransferRequests.build_payload("flaky")
        second = TransferRequests.build_payload("flaky")
        for payload in (first, first, second):
            with pytest.raises(requests.exceptions.ReadTimeout):
                impatient_transfers.post_transfer(payload)
        status, _ = transfers.post_transfer(first)
        assert status == 200


class TestInvalidBody:
    @pytest.mark.parametrize(
        "mutation, code",
        [
            (lambda payload: payload.pop("payout_key"), "RNV000007"),
            (lambda payload: payload.pop("amount_minor"), "RNV000007"),
            (lambda payload: payload.pop("purpose"), "RNV000007"),
            (lambda payload: payload.pop("destination"), "RNV000007"),
            (lambda payload: payload.update(payout_key="not-a-uuid"), "RNV000009"),
            (lambda payload: payload.update(payout_key=123), "RNV000009"),
            (lambda payload: payload.update(amount_minor=0), "RNV000010"),
            (lambda payload: payload.update(amount_minor=-5), "RNV000010"),
            (lambda payload: payload.update(amount_minor=10.5), "RNV000009"),
            (lambda payload: payload.update(amount_minor="100"), "RNV000009"),
            (lambda payload: payload.update(amount_minor=True), "RNV000009"),
            (lambda payload: payload.update(purpose=""), "RNV000010"),
            (lambda payload: payload.update(purpose=7), "RNV000009"),
            (lambda payload: payload.update(destination="bank"), "RNV000009"),
            (lambda payload: payload.update(destination=[]), "RNV000009"),
            (lambda payload: payload.update(extra="field"), "RNV000008"),
            (lambda payload: payload["destination"].update(scenario="explode"), "RNV000009"),
            (lambda payload: payload["destination"].update(scenario=1), "RNV000009"),
        ],
    )
    def test_rejects_with_invalid_schema(self, transfers, mutation, code):
        payload = copy.deepcopy(TransferRequests.build_payload())
        mutation(payload)
        status, response = transfers.post_transfer(payload)
        assert status == 400
        assert set(response) == ERROR_FIELDS
        assert response["code"] == code

    def test_rejects_a_body_that_is_not_json(self, api):
        status, response, _ = api.request_with_headers("POST", "/interbank/transfers")
        assert status == 400
        assert response["code"] == "RNV000001"

    def test_rejects_a_json_body_that_is_not_an_object(self, transfers):
        status, response = transfers.post_transfer([1, 2])
        assert status == 400
        assert response["code"] == "RNV000001"
