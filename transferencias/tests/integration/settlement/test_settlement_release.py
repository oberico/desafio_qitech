import pytest

from tests.integration.settlement.conftest import before_instant, due_instant, settlement_ledger_payload


class TestSettlementRelease:
    def test_releases_the_payment_whose_window_expired(self, settlements, payments, held_payment):
        payment = held_payment()

        status, response = settlements.run(due_instant(payment))

        assert status == 200
        assert payment["payment_key"] in response["settled"]
        assert payment["payment_key"] not in response["deferred"]
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "settled"

    def test_does_not_release_before_the_window_expires(self, settlements, payments, held_payment):
        payment = held_payment()

        status, response = settlements.run(before_instant(payment))

        assert status == 200
        assert payment["payment_key"] not in response["settled"]
        assert payment["payment_key"] not in response["deferred"]
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "held"

    def test_response_echoes_the_instant_used(self, settlements, held_payment):
        payment = held_payment()
        status, response = settlements.run("2026-10-12T12:00:00Z")
        assert status == 200
        assert response["as_of"].startswith("2026-10-12T12:00:00")


class TestSettlementLedger:
    @pytest.mark.parametrize(
        "amount_minor, fee_minor, net_minor",
        [(101, 1, 100), (10001, 100, 9901), (1, 1, 0), (100000, 990, 99010)],
        ids=["resid_101", "resid_10001", "net_zero", "exact"],
    )
    def test_ledger_entry_rounds_the_fee_up(
        self, settlements, held_payment, bank, internal_token, amount_minor, fee_minor, net_minor
    ):
        payment = held_payment(amount_minor=amount_minor)
        settlements.run(due_instant(payment))

        expected = settlement_ledger_payload(payment, net_minor, fee_minor)
        status, _ = bank.post_ledger_transaction(expected, f"settlement:{payment['payment_key']}", internal_token)

        assert status == 200

    def test_ledger_entry_differs_when_the_amounts_differ(self, settlements, held_payment, bank, internal_token):
        payment = held_payment(amount_minor=10001)
        settlements.run(due_instant(payment))

        wrong = settlement_ledger_payload(payment, 9900, 101)
        status, response = bank.post_ledger_transaction(wrong, f"settlement:{payment['payment_key']}", internal_token)

        assert status == 422
        assert response["code"] == "RNV001024"
