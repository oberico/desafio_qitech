from models import Payment


class PaymentDTO:
    @staticmethod
    def obj_to_dict(payment: Payment) -> dict:
        return {
            "payment_key": payment.payment_key,
            "company_key": payment.company_key,
            "account_key": payment.account_key,
            "transaction_key": payment.transaction_key,
            "origin": payment.origin.enumerator,
            "method": payment.method,
            "status": payment.status.enumerator,
            "amount_minor": payment.amount_minor,
            "fee_minor": payment.fee_minor,
            "release_at": payment.release_at.isoformat() if payment.release_at else None,
        }

    @staticmethod
    def only_obj_key(payment: Payment) -> dict:
        return {"payment_key": payment.payment_key}
