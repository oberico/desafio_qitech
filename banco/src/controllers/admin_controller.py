import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import AccountDTO, AdminClientDTO, CompanyDTO, LedgerTotalsDTO
from repositories import AccountRepository, ClientRepository, CompanyRepository, LedgerRepository
from utils.cursor import decode_cursor
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
        return self._list_page(query, self.client_repository, AdminClientDTO.obj_to_dict)

    def list_companies(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_PAGE_SCHEMA)
        return self._list_page(query, self.company_repository, CompanyDTO.obj_to_dict)

    def list_accounts(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_ACCOUNTS_SCHEMA)
        return self._list_page(
            query,
            self.account_repository,
            AccountDTO.obj_to_dict,
            status=query.get("status"),
        )

    def ledger_totals(self) -> dict:
        return LedgerTotalsDTO.obj_to_dict(self.ledger_repository.natural_balances_by_code())

    def _list_page(self, query: dict, repository, to_dict, **filters) -> dict:
        size = page_size(query)
        cursor = query.get("cursor")
        before_id = decode_cursor(cursor) if cursor is not None else None

        items = repository.list_newest_first(size + 1, before_id, **filters)
        return build_page(items, size, to_dict)
