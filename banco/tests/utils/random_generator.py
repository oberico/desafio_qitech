import random
from uuid import uuid4


class RandomGenerator:
    @staticmethod
    def uuid() -> str:
        return str(uuid4())

    @staticmethod
    def amount_minor(minimum: int = 100, maximum: int = 1_000_000) -> int:
        return random.randint(minimum, maximum)

    @staticmethod
    def cpf() -> str:
        digits = [random.randint(0, 9) for _ in range(9)]
        for weight_start in (10, 11):
            total = sum(d * w for d, w in zip(digits, range(weight_start, 1, -1)))
            digits.append(total * 10 % 11 % 10)
        d = "".join(map(str, digits))
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

    @staticmethod
    def email() -> str:
        return f"{uuid4().hex}@teste.com"

    @staticmethod
    def cnpj() -> str:
        digits = "".join(str(random.randint(0, 9)) for _ in range(14))
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
