from tests.integration.settlement.conftest import due_instant


class TestSettlementDeferred:
    def test_blocked_account_defers_and_the_payment_stays_held(self, settlements, payments, held_payment, bank, internal_token):
        payment = held_payment()
        bank.block_account(payment["account_key"], internal_token)

        status, response = settlements.run(due_instant(payment))

        assert status == 200
        assert payment["payment_key"] in response["deferred"]
        assert payment["payment_key"] not in response["settled"]
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "held"

    def test_releases_on_the_next_run_after_unblocking(self, settlements, payments, held_payment, bank, internal_token):
        payment = held_payment()
        as_of = due_instant(payment)
        bank.block_account(payment["account_key"], internal_token)
        settlements.run(as_of)

        bank.unblock_account(payment["account_key"], internal_token)
        status, response = settlements.run(as_of)

        assert status == 200
        assert payment["payment_key"] in response["settled"]
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "settled"

    def test_a_deferred_merchant_does_not_block_the_others(self, settlements, payments, held_payment, bank, internal_token):
        blocked = held_payment()
        healthy = held_payment()
        bank.block_account(blocked["account_key"], internal_token)

        _, response = settlements.run(due_instant(healthy))

        assert blocked["payment_key"] in response["deferred"]
        assert healthy["payment_key"] in response["settled"]
