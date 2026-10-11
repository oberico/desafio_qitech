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


class AdminForbidden(QIException):
    code = "RNV001027"

    def __init__(self) -> None:
        title = "Forbidden"
        http_status = 403
        description = "This route is restricted to administrators."
        translation = "Esta rota é restrita a administradores."
        super().__init__(title, self.code, http_status, description, translation)
