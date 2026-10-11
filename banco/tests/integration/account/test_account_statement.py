from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator


class TestAccountStatement:
    def test_new_account_has_empty_statement(self, accounts, active_account, client_token):
        status, response = accounts.get_statement(active_account, client_token)

        assert status == 200
        assert response["account_key"] == active_account
        assert response["entries"] == []
        assert response["has_more"] is False

    def test_statement_lists_newest_entries_first(self, accounts, active_account, client_token, credit_account):
        credit_account(active_account, 1000)
        credit_account(active_account, 2000)
        credit_account(active_account, 3000)

        status, response = accounts.get_statement(active_account, client_token)

        assert status == 200
        credits = [entry["credit_minor"] for entry in response["entries"]]
        assert credits == [3000, 2000, 1000]

    def test_statement_rebuilds_the_balance(self, accounts, ledger, active_account, client_token, credit_account):
        credit_account(active_account, 10000)
        payout = PayloadGenerator.create_ledger_transaction_payload(
            type="payout",
            entries=[
                {"account_key": active_account, "debit_minor": 3000},
                {"account_code": "in_transit", "credit_minor": 3000},
            ],
        )
        status, _ = ledger.post_transaction(payout, RandomGenerator.uuid())
        assert status == 201

        status, statement = accounts.get_statement(active_account, client_token)
        assert status == 200
        status, balance = accounts.get_balance(active_account, client_token)
        assert status == 200

        rebuilt = sum(entry["credit_minor"] - entry["debit_minor"] for entry in statement["entries"])
        assert rebuilt == balance["balance_minor"]

    def test_statement_shows_only_its_own_entries(self, accounts, open_account, active_account, client_token, other_client_token, credit_account):
        other_account = open_account(other_client_token)
        credit_account(other_account, 5000)
        transaction_key = credit_account(active_account, 10000)

        status, response = accounts.get_statement(active_account, client_token)

        assert status == 200
        assert [entry["transaction_key"] for entry in response["entries"]] == [transaction_key]