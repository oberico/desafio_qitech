from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestLedgerSameAccount:
    def test_refuses_debiting_and_crediting_the_same_internal_account(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "in_transit", "debit_minor": 500},
                {"account_code": "in_transit", "credit_minor": 500},
            ]
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 422
        assert response["code"] == "RNV001037"
        assert response["translation"] == "A conta in_transit não pode ser debitada e creditada no mesmo lançamento."

    def test_refuses_debiting_and_crediting_the_same_client_account(
        self, ledger, accounts, active_account, client_token, credit_account
    ):
        credit_account(active_account, 1000)
        payload = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 500},
                {"account_key": active_account, "credit_minor": 500},
            ],
        )
        status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 422
        assert response["code"] == "RNV001037"

        _, statement = accounts.get_statement(active_account, client_token)
        assert len(statement["data"]) == 1

    def test_same_account_twice_on_the_same_side_is_accepted(self, ledger):
        payload = PayloadGenerator.create_ledger_transaction_payload(
            entries=[
                {"account_code": "reserves", "debit_minor": 300},
                {"account_code": "reserves", "debit_minor": 200},
                {"account_code": "in_transit", "credit_minor": 500},
            ]
        )
        status, _ = ledger.post_transaction(payload, RandomGenerator.uuid())
        assert status == 201
