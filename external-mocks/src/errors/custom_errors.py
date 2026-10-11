from errors.base_error import QIException


class InvalidSchema(QIException):
    code = "RNV000001"

    def __init__(self, reason) -> None:
        title = "Invalid Schema"
        http_status = 400
        description = f"The request does not match the expected schema: {reason}"
        translation = "A requisição não está no formato esperado."
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
