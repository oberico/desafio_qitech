from concurrent.futures import ThreadPoolExecutor

from tests.integration.settlement.conftest import due_instant, settlement_ledger_payload


class TestSettlementIdempotency:
    def test_second_run_with_the_same_as_of_does_not_list_the_payment(self, settlements, held_payment):
        payment = held_payment()
        as_of = due_instant(payment)

        _, first = settlements.run(as_of)
        status, second = settlements.run(as_of)

        assert payment["payment_key"] in first["settled"]
        assert status == 200
        assert payment["payment_key"] not in second["settled"]
        assert payment["payment_key"] not in second["deferred"]

    def test_there_is_a_single_settlement_in_the_bank(self, settlements, held_payment, bank, internal_token):
        payment = held_payment(amount_minor=5000)
        as_of = due_instant(payment)
        settlements.run(as_of)
        settlements.run(as_of)

        expected = settlement_ledger_payload(payment, 4950, 50)
        status, transaction = bank.post_ledger_transaction(expected, f"settlement:{payment['payment_key']}", internal_token)

        assert status == 200
        assert transaction["transaction_key"] != payment["transaction_key"]

    def test_concurrent_runs_release_the_payment_exactly_once(self, settlements, payments, held_payment):
        payment = held_payment()
        as_of = due_instant(payment)

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: settlements.run(as_of), range(10)))

        assert all(status == 200 for status, _ in results)
        releases = sum(response["settled"].count(payment["payment_key"]) for _, response in results)
        assert releases == 1
        _, current = payments.get_payment(payment["payment_key"])
        assert current["status"] == "settled"
