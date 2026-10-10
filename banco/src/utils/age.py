from datetime import date


def age_on(birthdate: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
    return today.year - birthdate.year - (0 if had_birthday else 1)
