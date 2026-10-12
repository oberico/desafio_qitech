from models import Account


class AccountDTO:
    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        return {
            "account_key": account.account_key,
            "company_key": account.company.company_key,
            "status": account.status.enumerator,
            "currency": account.currency,
            "created_at": account.created_at.isoformat(),
        }
