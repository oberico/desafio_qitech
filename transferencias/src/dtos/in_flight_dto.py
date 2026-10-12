class InFlightDTO:
    @staticmethod
    def to_dict(held_payments: int, pending_payouts: int) -> dict:
        return {"held_payments": held_payments, "pending_payouts": pending_payouts}
