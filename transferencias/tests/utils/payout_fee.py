SEEDED_FEE_BPS = 50


def payout_fee_minor(amount_minor: int, fee_bps: int = SEEDED_FEE_BPS) -> int:
    return (amount_minor * fee_bps + 9999) // 10000
