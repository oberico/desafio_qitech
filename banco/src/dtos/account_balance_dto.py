from models import Account
from utils.money import format_brl


class AccountBalanceDTO:
    @staticmethod
    def obj_to_dict(account: Account, balance_minor: int) -> dict:
        return {
            "account_key": account.account_key,
            "balance_minor": int(balance_minor),
            "balance_formatted": format_brl(int(balance_minor)),
            "currency": account.currency,
        }
