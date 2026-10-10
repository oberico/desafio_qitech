class TestLedgerTransactionCreate:
    def test_refuses_missing_internal_token(self, api):
        status, response = api.post("/ledger/transactions", body={})
        assert status == 403
        assert response["code"] == "RNV000002"

    # def test_refuses_empty_body(self, api):
    #     ...

    # def test_create_transaction(self, api):
    #     ...

    # def test_refuses_unbalanced_entries(self, api):
    #     ...

    # def test_refuses_unknown_account(self, api):
    #     ... 

    # def test_refuses_inactive_account(self, api):
    #     ...

    # def test_refuses_insufficient_funds(self, api):
    #     ...

    # def test_refuses_unknwon_referenced_transaction(self, api):
    #     ...

    # def test_refuses_alredy_settled_or_reversed(self, api):
    #     ...

    # def test_replay_returns_200(self, api):
    #     ...

    # def test_refuses_reused_key_with_other_content(self, api):
    #     ...

   