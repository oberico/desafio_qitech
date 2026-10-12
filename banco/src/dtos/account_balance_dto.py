from models import Account


class AccountBalanceDTO:
    @staticmethod
    def obj_to_dict(account: Account, balance_minor: int) -> dict:
        return {
            "account_key":account.account_key,
            "balance_minor":int(balance_minor),
            "currency": account.currency,
        }