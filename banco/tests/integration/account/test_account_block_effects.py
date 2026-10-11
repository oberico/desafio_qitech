from concurrent.futures import ThreadPoolExecutor

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestAccountBlockEffects:
    def test_owner_cannot_close_a_blocked_account(self, accounts, blocked_account, client_token):
        status, response = accounts.close(blocked_account, client_token)

        assert status == 409
        assert response["code"] == "RNV001009"

        status, response = accounts.get_account(blocked_account, client_token)
        assert response["status"] == "blocked"

    def test_ledger_refuses_moving_money_into_a_blocked_account(self, ledger, blocked_account):
        receipt = PayloadGenerator.create_ledger_transaction_payload()
        status, receipt_response = ledger.post_transaction(receipt, RandomGenerator.uuid())
        assert status == 201

        settlement = PayloadGenerator.create_ledger_transaction_payload(
            type="settlement",
            settles_transaction_key=receipt_response["transaction_key"],
            entries=[
                {"account_code": "in_transit", "debit_minor": 10000},
                {"account_key": blocked_account, "credit_minor": 10000},
            ],
        )
        status, response = ledger.post_transaction(settlement, RandomGenerator.uuid())

        assert status == 422
        assert response["code"] == "RNV001005"

    def test_concurrent_blocks_let_only_one_through(self, accounts, active_account, internal_token):
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: accounts.block(active_account, internal_token), range(5)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [200] + [409] * 4

    def test_account_can_be_blocked_again_after_unblock(self, accounts, blocked_account, internal_token):
        status, _ = accounts.unblock(blocked_account, internal_token)
        assert status == 200

        status, response = accounts.block(blocked_account, internal_token)

        assert status == 200
        assert response["status"] == "blocked"