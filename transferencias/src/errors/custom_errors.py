from errors import QIException


class ForbiddenNotInternal(QIException):
    code = "RNV000002"

    def __init__(self) -> None:
        title = "Forbidden"
        http_status = 403
        description = "This route is restricted to internal services: the INTERNAL-TOKEN header is missing or invalid."
        translation = "Esta rota é restrita a serviços internos: o header INTERNAL-TOKEN está ausente ou inválido."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundRoute(QIException):
    code = "RNV000004"

    def __init__(self) -> None:
        title = "Route not Found"
        http_status = 404
        description = "The requested route does not exist."
        translation = "A rota solicitada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class ServiceBusy(QIException):
    code = "RNV000006"

    def __init__(self) -> None:
        title = "Service Busy"
        http_status = 503
        description = "The service is at capacity and could not take the request in time; retry shortly."
        translation = "O serviço está no limite de capacidade e não conseguiu atender a requisição a tempo; tente novamente em instantes."
        super().__init__(title, self.code, http_status, description, translation)


class MethodNotAllowed(QIException):
    code = "RNV000005"

    def __init__(self) -> None:
        title = "Method not Allowed"
        http_status = 405
        description = "The HTTP method is not allowed for this route."
        translation = "O método HTTP não é permitido para esta rota."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidAmount(QIException):
    code = "RNV001023"

    def __init__(self, amount_minor) -> None:
        title = "Invalid Amount"
        http_status = 422
        description = f"The amount {amount_minor} is not a valid payment amount."
        translation = "O valor do pagamento é inválido."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundPayment(QIException):
    code = "RNV001025"

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


class InvalidSchema(QIException):
    code = "RNV000001"

    def __init__(self, reason) -> None:
        title = "Invalid Schema"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = "A requisição não está no formato esperado."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidClientToken(QIException):
    code = "RNV000003"

    def __init__(self) -> None:
        title = "Unauthorized"
        http_status = 401
        description = "The Authorization token is missing, invalid or revoked."
        translation = "O token de autorização está ausente, é inválido ou foi revogado."
        super().__init__(title, self.code, http_status, description, translation)


class BankUnavailable(QIException):
    code = "RNV001017"

    def __init__(self) -> None:
        title = "Bank Unavailable"
        http_status = 503
        description = "The bank service is unavailable; nothing was recorded."
        translation = "O Banco está indisponível; nada foi gravado."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundCompany(QIException):
    code = "RNV001018"

    def __init__(self, company_key: str) -> None:
        title = "Company not Found"
        http_status = 404
        description = f"Company with key {company_key} was not found."
        translation = f"A empresa com chave {company_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class CompanyWithoutAccount(QIException):
    code = "RNV001030"

    def __init__(self) -> None:
        title = "Company Without Account"
        http_status = 403
        description = "The company has no open account."
        translation = "A empresa não possui conta aberta."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotActive(QIException):
    code = "RNV001031"

    def __init__(self) -> None:
        title = "Account Not Active"
        http_status = 403
        description = "The account is not active, so this operation is not allowed."
        translation = "A conta não está ativa, por isso esta operação não é permitida."
        super().__init__(title, self.code, http_status, description, translation)
