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
        digits = "".join(str(random.randint(0, 9)) for _ in range(11))
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    @staticmethod
    def cnpj() -> str:
        digits = "".join(str(random.randint(0, 9)) for _ in range(14))
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
