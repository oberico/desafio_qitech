import re

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator

ROUTE = "/admin/internal-accounts"
MINOR_FIELDS = {"reserves_minor", "in_transit_minor", "revenue_minor", "clients_total_minor"}
FORMATTED_FIELDS = {field.replace("_minor", "_formatted") for field in MINOR_FIELDS}
TOTAL_FIELDS = MINOR_FIELDS | FORMATTED_FIELDS | {"equation_ok"}
BRL_PATTERN = re.compile(r"^-?R\$ \d{1,3}(\.\d{3})*,\d{2}$")
AMOUNT = 1_000
FEE = 30


def ledger_totals(admin, admin_token) -> dict:
    status, response = admin.get(ROUTE, admin_token)
    assert status == 200, f"não deu para ler os totais do livro: {status} {response}"
    return response


def difference(before: dict, after: dict) -> dict:
    return {field: after[field] - before[field] for field in MINOR_FIELDS}


def brl(amount_minor: int) -> str:
    reais, cents = divmod(abs(amount_minor), 100)
    sign = "-" if amount_minor < 0 else ""
    return f"{sign}R$ {reais:,}".replace(",", ".") + f",{cents:02d}"


def post_receipt(ledger) -> str:
    payload = PayloadGenerator.create_ledger_transaction_payload(
        entries=[
            {"account_code": "reserves", "debit_minor": AMOUNT},
            {"account_code": "in_transit", "credit_minor": AMOUNT},
        ]
    )
    status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
    assert status == 201, f"não deu para lançar o recebimento: {status} {response}"
    return response["transaction_key"]


def post_settlement_to_client(ledger, receipt_key: str, account_key: str) -> None:
    payload = PayloadGenerator.create_ledger_transaction_payload(
        type="settlement",
        settles_transaction_key=receipt_key,
        entries=[
            {"account_code": "in_transit", "debit_minor": AMOUNT},
            {"account_key": account_key, "credit_minor": AMOUNT - FEE},
            {"account_code": "revenue", "credit_minor": FEE},
        ],
    )
    status, response = ledger.post_transaction(payload, RandomGenerator.uuid())
    assert status == 201, f"não deu para liberar o valor para o cliente: {status} {response}"


class TestAdminInternalAccounts:
    def test_returns_the_ledger_totals(self, admin, admin_token):
        response = ledger_totals(admin, admin_token)
        assert set(response) == TOTAL_FIELDS
        for field in MINOR_FIELDS:
            assert isinstance(response[field], int)

    def test_equation_closes(self, admin, admin_token):
        response = ledger_totals(admin, admin_token)
        assert response["equation_ok"] is True
        assert response["reserves_minor"] == (
            response["in_transit_minor"] + response["clients_total_minor"] + response["revenue_minor"]
        )

    def test_receipt_increases_reserves_and_in_transit(self, admin, admin_token, ledger):
        before = ledger_totals(admin, admin_token)
        post_receipt(ledger)
        after = ledger_totals(admin, admin_token)

        assert difference(before, after) == {
            "reserves_minor": AMOUNT,
            "in_transit_minor": AMOUNT,
            "clients_total_minor": 0,
            "revenue_minor": 0,
        }
        assert after["equation_ok"] is True

    def test_settlement_moves_money_from_in_transit_to_client_and_revenue(
        self, admin, admin_token, ledger, active_account
    ):
        receipt_key = post_receipt(ledger)
        before = ledger_totals(admin, admin_token)
        post_settlement_to_client(ledger, receipt_key, active_account)
        after = ledger_totals(admin, admin_token)

        assert difference(before, after) == {
            "reserves_minor": 0,
            "in_transit_minor": -AMOUNT,
            "clients_total_minor": AMOUNT - FEE,
            "revenue_minor": FEE,
        }
        assert after["equation_ok"] is True

    def test_each_total_comes_formatted_in_reais(self, admin, admin_token):
        response = ledger_totals(admin, admin_token)
        for field in FORMATTED_FIELDS:
            assert BRL_PATTERN.match(response[field]), f"{field} fora do formato: {response[field]!r}"

    def test_formatted_totals_match_the_minor_totals(self, admin, admin_token, ledger):
        post_receipt(ledger)
        response = ledger_totals(admin, admin_token)
        for field in MINOR_FIELDS:
            assert response[field.replace("_minor", "_formatted")] == brl(response[field])
