from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


def post_receipt(ledger) -> tuple:
    key = RandomGenerator.uuid()
    payload = PayloadGenerator.create_ledger_transaction_payload()
    status, response = ledger.post_transaction(payload, key)
    assert status == 201, f"não deu para lançar o recebimento: {status} {response}"
    return key, payload, response


class TestLedgerReplayReversed:
    def test_new_transaction_is_not_reversed(self, ledger):
        _, _, response = post_receipt(ledger)
        assert response["reversed"] is False

    def test_replay_of_a_refunded_receipt_says_it_was_reversed(self, ledger):
        key, payload, receipt = post_receipt(ledger)
        refund = PayloadGenerator.create_ledger_transaction_payload(
            type="refund", reverses_transaction_key=receipt["transaction_key"]
        )
        status, _ = ledger.post_transaction(refund, RandomGenerator.uuid())
        assert status == 201

        status, replay = ledger.post_transaction(payload, key)
        assert status == 200
        assert replay["transaction_key"] == receipt["transaction_key"]
        assert replay["reversed"] is True

    def test_replay_of_a_settled_receipt_is_not_reversed(self, ledger):
        key, payload, receipt = post_receipt(ledger)
        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement", settles_transaction_key=receipt["transaction_key"]
        )
        status, _ = ledger.post_transaction(settlement, RandomGenerator.uuid())
        assert status == 201

        status, replay = ledger.post_transaction(payload, key)
        assert status == 200
        assert replay["reversed"] is False
