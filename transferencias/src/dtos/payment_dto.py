from models import Payment


class PaymentDTO:
    @staticmethod
    def obj_to_dict(payment: Payment) -> dict:
        return {
            "payment_key": payment.payment_key,
            "company_key": payment.company_key,
            "account_key": payment.account_key,
            "transaction_key": payment.transaction_key,
            "method": payment.method.enumerator,
            "status": payment.status.enumerator,
            "amount_minor": payment.amount_minor,
            "fee_bps": payment.fee_bps,
            "release_at": payment.release_at.isoformat(),
        }
