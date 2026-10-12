from models import Account
from utils.money import format_brl


class LedgerTotalsDTO:
    @staticmethod
    def obj_to_dict(balances: dict) -> dict:
        reserves = balances.get(Account.RESERVES, 0)
        in_transit = balances.get(Account.IN_TRANSIT, 0)
        revenue = balances.get(Account.REVENUE, 0)
        clients_total = balances.get(Account.BUSINESS, 0)
        return {
            "reserves_minor": reserves,
            "reserves_formatted": format_brl(reserves),
            "in_transit_minor": in_transit,
            "in_transit_formatted": format_brl(in_transit),
            "revenue_minor": revenue,
            "revenue_formatted": format_brl(revenue),
            "clients_total_minor": clients_total,
            "clients_total_formatted": format_brl(clients_total),
            "equation_ok": reserves == in_transit + clients_total + revenue,
        }
