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

    def __init__(self, amount_minor: int, max_amount_minor: int) -> None:
        title = "Invalid Amount"
        http_status = 422
        if amount_minor <= 0:
            description = f"The amount {amount_minor} must be greater than zero."
            translation = "O valor precisa ser maior que zero."
        else:
            description = f"The amount {amount_minor} exceeds the maximum of {max_amount_minor}."
            translation = f"O valor passa do máximo permitido de {max_amount_minor} centavos."
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
        title = "Malformed Body"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = "O corpo da requisição precisa ser um objeto JSON."
        super().__init__(title, self.code, http_status, description, translation)


class MissingField(QIException):
    code = "RNV000007"

    def __init__(self, field: str, reason: str) -> None:
        title = "Missing Field"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = f"Campo obrigatório ausente: {field}."
        super().__init__(title, self.code, http_status, description, translation)


class FieldNotAllowed(QIException):
    code = "RNV000008"

    def __init__(self, field: str, reason: str, conflicting_field: str = None) -> None:
        title = "Field Not Allowed"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = f"Campo não permitido: {field}."
        if conflicting_field:
            translation += f" Não pode vir junto com {conflicting_field}."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidFormat(QIException):
    code = "RNV000009"

    def __init__(self, field: str, reason: str, expected: str) -> None:
        title = "Invalid Format"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = f"O campo {field} tem tipo ou formato inválido: {expected}."
        super().__init__(title, self.code, http_status, description, translation)


class ValueOutOfRange(QIException):
    code = "RNV000010"

    def __init__(self, field: str, reason: str, limit: str) -> None:
        title = "Value Out of Range"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = f"O campo {field} está fora do limite: {limit}."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidCursor(QIException):
    code = "RNV000011"

    def __init__(self) -> None:
        title = "Invalid Cursor"
        http_status = 400
        description = "The request does not match the expected schema: cursor: invalid cursor"
        translation = "O cursor é inválido: use o valor devolvido na página anterior, sem alterar."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidIdempotencyKey(QIException):
    code = "RNV000012"

    def __init__(self, reason: str, max_length: int) -> None:
        title = "Invalid Idempotency-Key"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = f"O header Idempotency-Key é obrigatório e deve ter de 1 a {max_length} caracteres."
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
        description = "The bank service is unavailable or did not answer in time; nothing was recorded in this service and the outcome at the bank may be unknown. Retry with the same Idempotency-Key."
        translation = "O Banco está indisponível ou não respondeu a tempo; nada foi gravado neste serviço e o resultado no Banco pode ser desconhecido. Retente com a mesma Idempotency-Key."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundCompany(QIException):
    code = "RNV001018"

    def __init__(self, key: str) -> None:
        title = "Company not Found"
        http_status = 404
        description = f"No company of this client matches the key {key}."
        translation = f"Nenhuma empresa deste cliente corresponde à chave {key}."
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


class PaymentOutsideWindow(QIException):
    code = "RNV001026"

    def __init__(self) -> None:
        title = "Outside Refund Window"
        http_status = 409
        description = "The payment was already released to the account and can no longer be refunded."
        translation = "O pagamento já foi liberado para a conta e não pode mais ser estornado."
        super().__init__(title, self.code, http_status, description, translation)


class PaymentAlreadyRefunded(QIException):
    code = "RNV001003"

    def __init__(self) -> None:
        title = "Payment Already Refunded"
        http_status = 409
        description = "The payment was already refunded."
        translation = "O pagamento já foi estornado."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundPayout(QIException):
    code = "RNV001032"

    def __init__(self, payout_key) -> None:
        title = "Payout not Found"
        http_status = 404
        description = f"Payout with key {payout_key} was not found."
        translation = f"O saque com chave {payout_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class BankRefused(QIException):
    def __init__(self, refusal: dict) -> None:
        super().__init__(
            refusal["title"],
            refusal["code"],
            422,
            refusal["description"],
            refusal["translation"],
        )


class AdminForbidden(QIException):
    code = "RNV001027"

    def __init__(self) -> None:
        title = "Forbidden"
        http_status = 403
        description = "This route is restricted to administrators."
        translation = "Esta rota é restrita a administradores."
        super().__init__(title, self.code, http_status, description, translation)
