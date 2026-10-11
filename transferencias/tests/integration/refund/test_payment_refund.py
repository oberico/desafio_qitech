from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from tests.integration.refund.conftest import refund_ledger_payload
from tests.integration.settlement.conftest import due_instant, settlement_ledger_payload

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestRefundAccess:
    def test_unknown_payment_is_not_found(self, payments):
        status, response = payments.refund_payment(str(uuid4()))
        assert status == 404
        assert response["code"] == "RNV001025"
        assert set(response) == ERROR_FIELDS

    def test_malformed_key_is_not_found(self, payments):
        status, response = payments.refund_payment("not-a-uuid")
        assert status == 404
        assert response["code"] == "RNV001025"

    def test_payment_of_another_client_is_not_found_and_stays_held(self, payments, other_payments, held_payment):
        payment = held_payment()

        status, response = other_payments.refund_payment(payment["payment_key"])

        assert status == 404
        assert response["code"] == "RNV001025"
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "held"


class TestRefundHappyPath:
    def test_refunds_a_held_payment(self, payments, held_payment):
        payment = held_payment()

        status, response = payments.refund_payment(payment["payment_key"])

        assert status == 200
        assert response["payment_key"] == payment["payment_key"]
        assert response["status"] == "refunded"
        assert response["amount_minor"] == payment["amount_minor"]

    def test_get_shows_refunded_afterwards(self, payments, held_payment):
        payment = held_payment()
        payments.refund_payment(payment["payment_key"])

        _, current = payments.get_payment(payment["payment_key"])

        assert current["status"] == "refunded"

    def test_refunds_even_when_the_window_already_expired_but_the_job_did_not_run(self, payments, held_payment):
        payment = held_payment()

        status, response = payments.refund_payment(payment["payment_key"])

        assert status == 200
        assert response["status"] == "refunded"


class TestRefundLedger:
    def test_bank_holds_the_full_amount_refund_under_the_refund_key(self, payments, held_payment, bank, internal_token):
        payment = held_payment()
        payments.refund_payment(payment["payment_key"])

        status, _ = bank.post_ledger_transaction(
            refund_ledger_payload(payment), f"refund:{payment['payment_key']}", internal_token
        )

        assert status == 200

    def test_bank_refund_differs_when_the_amount_differs(self, payments, held_payment, bank, internal_token):
        payment = held_payment()
        payments.refund_payment(payment["payment_key"])

        status, response = bank.post_ledger_transaction(
            refund_ledger_payload(payment, payment["amount_minor"] - 1), f"refund:{payment['payment_key']}", internal_token
        )

        assert status == 422
        assert response["code"] == "RNV001024"


class TestRefundStateGuard:
    def test_settled_payment_cannot_be_refunded(self, payments, settlements, held_payment):
        payment = held_payment()
        settlements.run(due_instant(payment))

        status, response = payments.refund_payment(payment["payment_key"])

        assert status == 409
        assert response["code"] == "RNV001026"
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "settled"

    def test_second_refund_is_refused(self, payments, held_payment):
        payment = held_payment()
        payments.refund_payment(payment["payment_key"])

        status, response = payments.refund_payment(payment["payment_key"])

        assert status == 409
        assert response["code"] == "RNV001003"

    def test_second_refund_leaves_a_single_ledger_entry(self, payments, held_payment, bank, internal_token):
        payment = held_payment()
        payments.refund_payment(payment["payment_key"])
        payments.refund_payment(payment["payment_key"])

        status, _ = bank.post_ledger_transaction(
            refund_ledger_payload(payment), f"refund:{payment['payment_key']}", internal_token
        )

        assert status == 200

    def test_refunded_payment_is_not_released_by_the_job(self, payments, settlements, held_payment):
        payment = held_payment()
        payments.refund_payment(payment["payment_key"])

        status, response = settlements.run(due_instant(payment))

        assert status == 200
        assert payment["payment_key"] not in response["settled"]
        assert payment["payment_key"] not in response["deferred"]
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "refunded"


class TestRefundConcurrency:
    def test_ten_simultaneous_refunds_yield_a_single_success(self, payments, held_payment):
        payment = held_payment()

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: payments.refund_payment(payment["payment_key"]), range(10)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [200] + [409] * 9
        assert all(response["code"] == "RNV001003" for status, response in results if status == 409)

    @pytest.mark.parametrize("round_number", range(5))
    def test_refund_racing_the_settlement_job_has_a_single_winner(
        self, payments, settlements, held_payment, bank, internal_token, round_number
    ):
        payment = held_payment()
        key = payment["payment_key"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            refund_future = pool.submit(payments.refund_payment, key)
            job_future = pool.submit(settlements.run, due_instant(payment))
            refund_status, refund_response = refund_future.result()
            job_status, job_response = job_future.result()

        assert job_status == 200
        _, current = payments.get_payment(key)
        fee_minor = (payment["amount_minor"] * payment["fee_bps"] + 9999) // 10000
        settlement_payload = settlement_ledger_payload(payment, payment["amount_minor"] - fee_minor, fee_minor)
        refund_payload = refund_ledger_payload(payment)

        if current["status"] == "refunded":
            assert refund_status == 200
            assert key not in job_response["settled"]
            winner = bank.post_ledger_transaction(refund_payload, f"refund:{key}", internal_token)
            loser = bank.post_ledger_transaction(settlement_payload, f"settlement:{key}", internal_token)
        else:
            assert current["status"] == "settled"
            assert refund_status == 409
            assert refund_response["code"] == "RNV001026"
            assert key in job_response["settled"]
            winner = bank.post_ledger_transaction(settlement_payload, f"settlement:{key}", internal_token)
            loser = bank.post_ledger_transaction(refund_payload, f"refund:{key}", internal_token)

        assert winner[0] == 200
        assert loser[0] not in (200, 201)
