from models import Payout


class PayoutDTO:
    @staticmethod
    def obj_to_dict(payout: Payout, attempts: int) -> dict:
        return {
            "payout_key": payout.payout_key,
            "company_key": payout.company_key,
            "account_key": payout.account_key,
            "purpose": payout.purpose.enumerator,
            "destination": payout.destination,
            "status": payout.status.enumerator,
            "amount_minor": payout.amount_minor,
            "failure_reason": payout.failure_reason,
            "transaction_key": payout.transaction_key,
            "attempts": attempts,
            "last_attempt_at": payout.last_attempt_at.isoformat() if payout.last_attempt_at else None,
        }
