from errors import QIException


class InvalidAmount(QIException):
    code = "RNV001020"

    def __init__(self, amount_minor) -> None:
        title = "Invalid Amount"
        http_status = 422
        description = f"The amount {amount_minor} is not a valid payment amount."
        translation = "O valor do pagamento é inválido."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundPayment(QIException):
    code = "RNV001022"

    def __init__(self, payment_key) -> None:
        title = "Payment not Found"
        http_status = 404
        description = f"Payment with key {payment_key} was not found."
        translation = f"O pagamento com chave {payment_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyKeyReused(QIException):
    code = "RNV001024"

    def __init__(self, idempotency_key) -> None:
        title = "Idempotency Key Reused"
        http_status = 422
        description = f"The idempotency key {idempotency_key} was already used with a different payload."
        translation = "Esta chave de idempotência já foi usada com outro conteúdo."
        super().__init__(title, self.code, http_status, description, translation)
