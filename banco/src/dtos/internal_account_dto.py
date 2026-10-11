from models import Account


class InternalAccountDTO:
    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        return {
            "account_key": account.account_key,
            "code": account.code,
            "class": account.account_class.enumerator,
            "normal_balance": account.normal_balance,
            "status": account.status.enumerator,
        }
