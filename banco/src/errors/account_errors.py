from errors.base_error import QIException


class AccountNotFound(QIException):
    code = "RNV001021"

    def __init__(self, account_key: str) -> None:
        title = "Account not Found"
        http_status = 404
        description = f"Account with key {account_key} was not found."
        translation = f"A conta com chave {account_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class CompanyAlreadyHasAccount(QIException):
    code = "RNV001022"

    def __init__(self) -> None:
        title = "Company Already Has Account"
        http_status = 409
        description = "This company already has an account."
        translation = "Esta empresa já possui uma conta aberta."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotActive(QIException):
    code = "RNV001009"

    def __init__(self) -> None:
        title = "Account Not Active"
        http_status = 409
        description = "Only an active account can be closed."
        translation = "Só uma conta ativa pode ser encerrada."
        super().__init__(title, self.code, http_status, description, translation)
