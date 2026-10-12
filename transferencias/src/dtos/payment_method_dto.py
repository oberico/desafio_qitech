from models import PaymentMethod


class PaymentMethodDTO:
    @staticmethod
    def obj_to_dict(method: PaymentMethod) -> dict:
        return {
            "method": method.enumerator,
            "version": method.version,
            "fee_bps": method.fee_bps,
            "release_window_hours": method.release_window_hours,
            "created_at": method.created_at.isoformat(),
        }
