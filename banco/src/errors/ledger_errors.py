from errors.base_error import QIException


class LedgerAccountNotActive(QIException):
    code = "RNV001005"

    def __init__(self, account_key: str) -> None:
        title = "Account not Active"
        http_status = 422
        description = f"The account {account_key} is not active and cannot receive ledger entries."
        translation = f"A conta {account_key} não está ativa e não pode receber lançamentos."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientFunds(QIException):
    code = "RNV001006"

    def __init__(self) -> None:
        title = "Insufficient Funds"
        http_status = 422
        description = "The account balance does not cover this debit."
        translation = "O saldo da conta não cobre este débito."
        super().__init__(title, self.code, http_status, description, translation)


class TransactionAlreadyConsumed(QIException):
    code = "RNV001014"

    def __init__(self, transaction_key: str) -> None:
        title = "Transaction Already Consumed"
        http_status = 409
        description = f"The transaction {transaction_key} was already settled or reversed."
        translation = f"A transação {transaction_key} já foi liquidada ou estornada."
        super().__init__(title, self.code, http_status, description, translation)


class UnbalancedEntries(QIException):
    code = "RNV001015"

    def __init__(self, total_debit: int, total_credit: int) -> None:
        title = "Unbalanced Entries"
        http_status = 422
        description = f"Debits ({total_debit}) and credits ({total_credit}) must match."
        translation = "A soma dos débitos precisa ser igual à soma dos créditos."
        super().__init__(title, self.code, http_status, description, translation)


class LedgerTransactionNotFound(QIException):
    code = "RNV001016"

    def __init__(self, transaction_key: str) -> None:
        title = "Transaction not Found"
        http_status = 404
        description = f"The referenced transaction {transaction_key} does not exist."
        translation = f"A transação {transaction_key} citada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyKeyReused(QIException):
    code = "RNV001024"

    def __init__(self, idempotency_key: str) -> None:
        title = "Idempotency Key Reused"
        http_status = 422
        description = f"The idempotency key {idempotency_key} was already used with a different payload."
        translation = "Esta chave de idempotência já foi usada com outro conteúdo."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidTransactionReference(QIException):
    code = "RNV001033"

    def __init__(self, transaction_key: str, transaction_type: str) -> None:
        title = "Invalid Transaction Reference"
        http_status = 422
        description = f"The transaction {transaction_key} is a {transaction_type} and cannot be referenced by this operation."
        translation = f"A transação {transaction_key} é do tipo {transaction_type} e não pode ser referenciada por esta operação."
        super().__init__(title, self.code, http_status, description, translation)
