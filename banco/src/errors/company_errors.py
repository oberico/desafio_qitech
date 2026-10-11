from errors.base_error import QIException


class CompanyNotFound(QIException):
    code = "RNV001018"

    def __init__(self, company_key: str) -> None:
        title = "Company not Found"
        http_status = 404
        description = f"Company with key {company_key} was not found."
        translation = f"A empresa com chave {company_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class CnpjAlreadyRegistered(QIException):
    code = "RNV001019"

    def __init__(self) -> None:
        title = "CNPJ Already Registered"
        http_status = 409
        description = "There is already a company registered with this CNPJ."
        translation = "Já existe uma empresa cadastrada com este CNPJ."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidCnpj(QIException):
    code = "RNV001020"

    def __init__(self, cnpj: str) -> None:
        title = "Invalid CNPJ"
        http_status = 422
        description = f"The CNPJ {cnpj} has invalid check digits."
        translation = f"O CNPJ {cnpj} tem dígitos verificadores inválidos."
        super().__init__(title, self.code, http_status, description, translation)
