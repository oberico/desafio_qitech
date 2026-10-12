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
        description = "The account is not active, so this operation is not allowed."
        translation = "A conta não está ativa, por isso esta operação não é permitida."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotBlocked(QIException):
    code = "RNV001010"

    def __init__(self) -> None:
        title = "Account Not Blocked"
        http_status = 409
        description = "The account is not blocked, so it cannot be unblocked."
        translation = "A conta não está bloqueada, por isso não pode ser desbloqueada."
        super().__init__(title, self.code, http_status, description, translation)


class AccountHasFundsInFlight(QIException):
    code = "RNV001035"

    def __init__(self) -> None:
        title = "Account Has Funds or Values In Transit"
        http_status = 422
        description = "The account has a balance or values in transit; closing requires a zero balance and nothing pending."
        translation = "Conta com saldo ou valores em trânsito; encerramento exige saldo zero e nada pendente."
        super().__init__(title, self.code, http_status, description, translation)
