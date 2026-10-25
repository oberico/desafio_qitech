from models import PayoutFee


class PayoutFeeDTO:
    @staticmethod
    def obj_to_dict(fee: PayoutFee) -> dict:
        return {
            "version": fee.version,
            "fee_bps": fee.fee_bps,
            "created_at": fee.created_at.isoformat(),
        }
