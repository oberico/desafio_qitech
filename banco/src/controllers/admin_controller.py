import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import AccountDTO, AdminClientDTO, CompanyDTO, LedgerTotalsDTO
from errors import InvalidSchema
from repositories import AccountRepository, ClientRepository, CompanyRepository, LedgerRepository
from utils.pagination import build_page, page_size
from utils.schema_handler import validate_json

GET_ADMIN_PAGE_SCHEMA = os.path.join(SCHEMAS_DIR, "get_admin_page.json")
GET_ADMIN_ACCOUNTS_SCHEMA = os.path.join(SCHEMAS_DIR, "get_admin_accounts.json")


class AdminController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.client_repository = ClientRepository(session)
        self.company_repository = CompanyRepository(session)
        self.account_repository = AccountRepository(session)
        self.ledger_repository = LedgerRepository(session)

    def list_clients(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_PAGE_SCHEMA)
        return self._list_page(query, self.client_repository, AdminClientDTO.obj_to_dict, lambda client: client.client_key)

    def list_companies(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_PAGE_SCHEMA)
        return self._list_page(query, self.company_repository, CompanyDTO.obj_to_dict, lambda company: company.company_key)

    def list_accounts(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_ACCOUNTS_SCHEMA)
        return self._list_page(
            query,
            self.account_repository,
            AccountDTO.obj_to_dict,
            lambda account: account.account_key,
            status=query.get("status"),
        )

    def ledger_totals(self) -> dict:
        return LedgerTotalsDTO.obj_to_dict(self.ledger_repository.natural_balances_by_code())

    def _list_page(self, query: dict, repository, to_dict, key_of, **filters) -> dict:
        size = page_size(query)
        before_id = self._cursor_id(query.get("cursor"), repository.get_by_key)

        items = repository.list_newest_first(size + 1, before_id, **filters)
        return build_page(items, size, to_dict, key_of)

    @staticmethod
    def _cursor_id(cursor: str, find_by_key) -> int:
        if cursor is None:
            return None
        item = find_by_key(cursor)
        if item is None:
            raise InvalidSchema(f"cursor: {cursor} does not point to an existing item")
        return item.id
