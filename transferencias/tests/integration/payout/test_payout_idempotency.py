from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.integration.payout.conftest import payout_ledger_payload


class TestPayoutIdempotency:
    def test_replay_returns_current_state_with_200(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload()

        status, first = payouts.post_payout(payload, key)
        assert status == 201

        status, second = payouts.post_payout(payload, key)
        assert status == 200
        assert second == first

    def test_same_destination_in_other_order_is_replay(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload(destination={"bank_code": "341", "agency": "0001"})
        reordered = {**payload, "destination": {"agency": "0001", "bank_code": "341"}}

        _, first = payouts.post_payout(payload, key)
        status, second = payouts.post_payout(reordered, key)

        assert status == 200
        assert second["payout_key"] == first["payout_key"]

    def test_reused_key_with_other_amount_is_refused(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload()
        payouts.post_payout(payload, key)

        status, response = payouts.post_payout({**payload, "amount_minor": payload["amount_minor"] + 1}, key)

        assert status == 422
        assert response["code"] == "RNV001024"

    def test_reused_key_with_other_destination_is_refused(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload()
        payouts.post_payout(payload, key)

        status, response = payouts.post_payout({**payload, "destination": {"bank_code": "999"}}, key)

        assert status == 422
        assert response["code"] == "RNV001024"

    def test_reused_key_with_other_purpose_is_refused(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload(purpose="withdrawal")
        payouts.post_payout(payload, key)

        status, response = payouts.post_payout({**payload, "purpose": "transfer"}, key)

        assert status == 422
        assert response["code"] == "RNV001024"

    def test_reused_key_with_other_scenario_is_refused(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload(destination={"bank_code": "341", "scenario": "confirm"})
        payouts.post_payout(payload, key)

        status, response = payouts.post_payout({**payload, "destination": {"bank_code": "341", "scenario": "refuse"}}, key)

        assert status == 422
        assert response["code"] == "RNV001024"

    def test_same_key_in_other_company_is_a_new_payout(self, payouts, payout_payload):
        key = str(uuid4())

        status, first = payouts.post_payout(payout_payload(), key)
        assert status == 201

        status, second = payouts.post_payout(payout_payload(), key)
        assert status == 201
        assert second["payout_key"] != first["payout_key"]
        assert second["transaction_key"] != first["transaction_key"]

    def test_retry_does_not_debit_twice(self, payouts, payout_payload):
        key = str(uuid4())
        payload = payout_payload(funding_minor=1000, amount_minor=1000)

        status, _ = payouts.post_payout(payload, key)
        assert status == 201
        status, _ = payouts.post_payout(payload, key)
        assert status == 200

        status, response = payouts.post_payout(payload, str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001006"

    def test_concurrent_requests_create_one_payout_and_one_debit(self, payouts, payout_payload, bank, internal_token):
        key = str(uuid4())
        payload = payout_payload(funding_minor=1000, amount_minor=1000)

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: payouts.post_payout(payload, key), range(10)))

        assert sorted(status for status, _ in results) == [200] * 9 + [201]
        assert len({response["payout_key"] for _, response in results}) == 1
        assert len({response["transaction_key"] for _, response in results}) == 1

        payout = results[0][1]
        status, transaction = bank.post_ledger_transaction(
            payout_ledger_payload(payout), f"payout:{payout['company_key']}:{key}", internal_token
        )
        assert status == 200
        assert transaction["transaction_key"] == payout["transaction_key"]

        status, response = payouts.post_payout(payload, str(uuid4()))
        assert status == 422
        assert response["code"] == "RNV001006"
