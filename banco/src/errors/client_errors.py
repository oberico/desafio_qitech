from errors.base_error import QIException


class CpfAlreadyRegistered(QIException):
    code = "RNV001001"

    def __init__(self) -> None:
        title = "CPF Already Registered"
        http_status = 409
        description = "There is already a client registered with this CPF."
        translation = "Já existe um cliente cadastrado com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidCpf(QIException):
    code = "RNV001002"

    def __init__(self, cpf: str) -> None:
        title = "Invalid CPF"
        http_status = 422
        description = f"The CPF {cpf} has invalid check digits."
        translation = f"O CPF {cpf} tem dígitos verificadores inválidos."
        super().__init__(title, self.code, http_status, description, translation)


class EmailAlreadyRegistered(QIException):
    code = "RNV001028"

    def __init__(self) -> None:
        title = "Email Already Registered"
        http_status = 409
        description = "There is already a client registered with this email."
        translation = "Já existe um cliente cadastrado com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageClient(QIException):
    code = "RNV001029"

    def __init__(self) -> None:
        title = "Underage Client"
        http_status = 422
        description = "The client must be at least 18 years old."
        translation = "A pessoa precisa ter pelo menos 18 anos."
        super().__init__(title, self.code, http_status, description, translation)
