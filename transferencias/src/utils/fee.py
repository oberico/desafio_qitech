BPS_DENOMINATOR = 10000


def split_fee(amount_minor: int, fee_bps: int) -> tuple[int, int]:
    if not isinstance(amount_minor, int) or not isinstance(fee_bps, int):
        raise TypeError("amount_minor and fee_bps must be integers")
    if amount_minor <= 0:
        raise ValueError("amount_minor must be positive")
    if not 0 <= fee_bps <= BPS_DENOMINATOR:
        raise ValueError("fee_bps must be between 0 and 10000")

    fee_minor = -(-amount_minor * fee_bps // BPS_DENOMINATOR)
    net_minor = amount_minor - fee_minor
    return fee_minor, net_minor
