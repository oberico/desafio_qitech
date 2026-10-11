from uuid import uuid4

from connectors import MockBureauConnector
from connectors.mock_bureau_connector import REJECTION_REASON
from controllers.base_controller import BaseController
from dtos import AccountDTO
from errors import AccountNotActive, AccountNotBlocked, AccountNotFound, CompanyAlreadyHasAccount, CompanyNotFound
from models import Account, AccountClass, AccountStatus
from repositories import AccountRepository, CompanyRepository

CLIENT_ACCOUNT_NORMAL_BALANCE = "c"
CONSTRAINT_ERRORS = {"account_company_id_key": CompanyAlreadyHasAccount}


class AccountController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.account_repository = AccountRepository(session)
        self.company_repository = CompanyRepository(session)
        self.bureau_connector = MockBureauConnector()

    def open(self, company_key: str, client_id: int) -> dict:
        company = self.company_repository.lock_by_key_and_client(company_key, client_id)
        if company is None:
            raise CompanyNotFound(company_key)
        if self.account_repository.exists_for_company(company.id):
            raise CompanyAlreadyHasAccount()

        created = self.account_repository.get_status(AccountStatus.CREATED)
        account = Account(
            account_key=str(uuid4()),
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
