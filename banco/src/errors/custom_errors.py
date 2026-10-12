from errors import QIException


class ForbiddenNotInternal(QIException):
    code = "RNV000002"

    def __init__(self) -> None:
        title = "Forbidden"
        http_status = 403
        description = "This route is restricted to internal services: the INTERNAL-TOKEN header is missing or invalid."
        translation = "Esta rota é restrita a serviços internos: o header INTERNAL-TOKEN está ausente ou inválido."
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


class NotFoundRoute(QIException):
    code = "RNV000004"

    def __init__(self) -> None:
        title = "Route not Found"
        http_status = 404
        description = "The requested route does not exist."
        translation = "A rota solicitada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class MethodNotAllowed(QIException):
    code = "RNV000005"

    def __init__(self) -> None:
        title = "Method not Allowed"
        http_status = 405
        description = "The HTTP method is not allowed for this route."
        translation = "O método HTTP não é permitido para esta rota."
        super().__init__(title, self.code, http_status, description, translation)


class TransferenciasUnavailable(QIException):
    code = "RNV001036"

    def __init__(self) -> None:
        title = "Transferencias Unavailable"
        http_status = 503
        description = "The transferencias service is unavailable or did not answer in time, so the values in transit could not be checked; nothing was changed. Retry shortly."
        translation = "O serviço de Transferências está indisponível ou não respondeu a tempo, então não foi possível conferir os valores em trânsito; nada foi alterado. Tente novamente em instantes."
        super().__init__(title, self.code, http_status, description, translation)


class AdminForbidden(QIException):
    code = "RNV001027"

    def __init__(self) -> None:
        title = "Forbidden"
        http_status = 403
        description = "This route is restricted to administrators."
        translation = "Esta rota é restrita a administradores."
        super().__init__(title, self.code, http_status, description, translation)
