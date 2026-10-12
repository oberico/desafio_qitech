def format_brl(amount_minor: int) -> str:
    reais, cents = divmod(abs(amount_minor), 100)
    sign = "-" if amount_minor < 0 else ""
    thousands = f"{reais:,}".replace(",", ".")
    return f"{sign}R$ {thousands},{cents:02d}"
