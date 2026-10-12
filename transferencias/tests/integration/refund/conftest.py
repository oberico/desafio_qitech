from tests.integration.settlement.conftest import due_instant, held_payment, settlements


def refund_ledger_payload(payment: dict, amount_minor: int = None) -> dict:
    amount_minor = payment["amount_minor"] if amount_minor is None else amount_minor
    return {
        "type": "refund",
        "reverses_transaction_key": payment["transaction_key"],
        "entries": [
            {"account_code": "in_transit", "debit_minor": amount_minor},
            {"account_code": "reserves", "credit_minor": amount_minor},
        ],
    }
