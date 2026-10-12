import os
from datetime import datetime
from uuid import uuid4

from connectors import MockBureauConnector
from connectors.mock_bureau_connector import REJECTION_REASON
from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import AccountBalanceDTO, AccountDTO, AccountStatementDTO, InternalAccountDTO
from errors import (
    AccountNotActive,
    AccountNotBlocked,
    AccountNotFound,
    CompanyAlreadyHasAccount,
    CompanyNotFound,
    InvalidSchema,
)
from models import Account, AccountClass, AccountStatus
from repositories import AccountRepository, CompanyRepository, LedgerRepository
from utils.cursor import decode_cursor, encode_cursor
from utils.schema_handler import validate_json

CLIENT_ACCOUNT_NORMAL_BALANCE = "c"
CONSTRAINT_ERRORS = {"account_company_id_key": CompanyAlreadyHasAccount}
DEFAULT_STATEMENT_LIMIT = 50
GET_ACCOUNT_STATEMENT_SCHEMA = os.path.join(SCHEMAS_DIR, "get_account_statement.json")


class AccountController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.account_repository = AccountRepository(session)
        self.company_repository = CompanyRepository(session)
        self.ledger_repository = LedgerRepository(session)
        self.bureau_connector = MockBureauConnector()
        
    def list_internal(self) -> list:
        return [InternalAccountDTO.obj_to_dict(account) for account in self.account_repository.list_internal()]

    def open(self, company_key: str, client_id: int) -> dict:
        company = self.company_repository.lock_by_key_and_client(company_key, client_id)
        if company is None:
            raise CompanyNotFound(company_key)
        if self.account_repository.exists_for_company(company.id):
            raise CompanyAlreadyHasAccount()

        created = self.account_repository.get_status(AccountStatus.CREATED)
        account = Account(
            account_key=str(uuid4()),
            code=Account.BUSINESS,
            company=company,
            class_id=self.account_repository.get_class(AccountClass.LIABILITY).id,
            status=created,
            normal_balance=CLIENT_ACCOUNT_NORMAL_BALANCE,
        )
        violated_constraint = self.account_repository.try_create(account)
        if violated_constraint:
            raise CONSTRAINT_ERRORS[violated_constraint]()
        self.account_repository.change_status(account, created)

        if self.bureau_connector.approves(company.cnpj):
            self.account_repository.change_status(account, self.account_repository.get_status(AccountStatus.ACTIVE))
        else:
            rejected = self.account_repository.get_status(AccountStatus.REJECTED)
            self.account_repository.change_status(account, rejected, REJECTION_REASON)

        account_dto = AccountDTO.obj_to_dict(account)
        self.session.commit()
        return account_dto

    def get_by_key(self, account_key: str, client_id: int) -> dict:
        account = self.account_repository.get_by_key_and_client(account_key, client_id)
        if account is None:
            raise AccountNotFound(account_key)
        return AccountDTO.obj_to_dict(account)

    def get_balance(self, account_key: str, client_id: int) -> dict:
        account = self.account_repository.get_by_key_and_client(account_key, client_id)
        if account is None:
            raise AccountNotFound(account_key)
        return AccountBalanceDTO.obj_to_dict(account, self.ledger_repository.balance_of(account.id))

    def get_statement(self, account_key: str, client_id: int, params: dict) -> dict:
        validate_json(params, GET_ACCOUNT_STATEMENT_SCHEMA)
        limit = int(params.get("limit", DEFAULT_STATEMENT_LIMIT))
        before_entry_id = decode_cursor(params["cursor"]) if "cursor" in params else None
        created_from = self._parse_datetime(params, "from")
        created_to = self._parse_datetime(params, "to")
        if created_from and created_to and created_from > created_to:
            raise InvalidSchema("from: must not be after to")

        account = self.account_repository.get_by_key_and_client(account_key, client_id)
        if account is None:
            raise AccountNotFound(account_key)

        rows = self.ledger_repository.list_statement(account.id, before_entry_id, created_from, created_to, limit + 1)
        page = rows[:limit]
        cursor = encode_cursor(page[-1][0].id) if len(rows) > limit else None
        return AccountStatementDTO.obj_to_dict(page, limit, cursor)

    @staticmethod
    def _parse_datetime(params: dict, field: str) -> datetime:
        if field not in params:
            return None
        try:
            return datetime.fromisoformat(params[field])
        except ValueError:
            raise InvalidSchema(f"{field}: invalid date")

    def close(self, account_key: str, client_id: int) -> dict:
        account = self.account_repository.lock_by_key_and_client(account_key, client_id)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive()

        self.account_repository.change_status(account, self.account_repository.get_status(AccountStatus.CLOSED))

        account_dto = AccountDTO.obj_to_dict(account)
        self.session.commit()
        return account_dto

    def block(self, account_key: str) -> dict:
        account = self.account_repository.lock_client_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive()

        self.account_repository.change_status(account, self.account_repository.get_status(AccountStatus.BLOCKED))

        account_dto = AccountDTO.obj_to_dict(account)
        self.session.commit()
        return account_dto

    def unblock(self, account_key: str) -> dict:
        account = self.account_repository.lock_client_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != AccountStatus.BLOCKED:
            raise AccountNotBlocked()

        self.account_repository.change_status(account, self.account_repository.get_status(AccountStatus.ACTIVE))

        account_dto = AccountDTO.obj_to_dict(account)
        self.session.commit()
        return account_dto
