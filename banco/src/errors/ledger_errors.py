from errors import QIException


class UnbalancedEntries(QIException):
    code = "RNV001030"

    def __init__(self, total_debit: int, total_credit: int) -> None:
        title = "Unbalanced Entries"
        http_status = 422
        description = f"Debits ({total_debit}) and credits ({total_credit}) must match, with at least two entries."
        translation = "A soma dos débitos precisa ser igual à soma dos créditos, com pelo menos dois lançamentos."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientFunds(QIException):
    code = "RNV001031"

    def __init__(self) -> None:
        title = "Insufficient Funds"
        http_status = 422
        description = "The account balance does not cover this debit."
        translation = "O saldo da conta não cobre este débito."
        super().__init__(title, self.code, http_status, description, translation)


class LedgerAccountNotFound(QIException):
    code = "RNV001032"

    def __init__(self, reference: str) -> None:
        title = "Ledger Account not Found"
        http_status = 422
        description = f"The account {reference} referenced by an entry does not exist."
        translation = f"A conta {reference} citada no lançamento não existe."
        super().__init__(title, self.code, http_status, description, translation)


class LedgerTransactionNotFound(QIException):
    code = "RNV001033"

    def __init__(self, transaction_key: str) -> None:
        title = "Ledger Transaction not Found"
        http_status = 422
        description = f"The referenced transaction {transaction_key} does not exist."
        translation = f"A transação {transaction_key} citada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class TransactionAlreadySettled(QIException):
    code = "RNV001034"

    def __init__(self) -> None:
        title = "Transaction Already Settled"
        http_status = 409
        description = "The referenced transaction was already consumed by another settlement."
        translation = "A transação citada já foi liquidada por outra operação."
        super().__init__(title, self.code, http_status, description, translation)


class TransactionAlreadyReversed(QIException):
    code = "RNV001035"

    def __init__(self) -> None:
        title = "Transaction Already Reversed"
        http_status = 409
        description = "The referenced transaction was already reversed."
        translation = "A transação citada já foi estornada."
        super().__init__(title, self.code, http_status, description, translation)
