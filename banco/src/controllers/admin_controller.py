import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import AdminClientDTO, CompanyDTO
from errors import InvalidSchema
from repositories import ClientRepository, CompanyRepository
from utils.pagination import build_page, page_size
from utils.schema_handler import validate_json

GET_ADMIN_PAGE_SCHEMA = os.path.join(SCHEMAS_DIR, "get_admin_page.json")


class AdminController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.client_repository = ClientRepository(session)
        self.company_repository = CompanyRepository(session)

    def list_clients(self, query: dict) -> dict:
        return self._list_page(query, self.client_repository, AdminClientDTO.obj_to_dict, lambda client: client.client_key)

    def list_companies(self, query: dict) -> dict:
        return self._list_page(query, self.company_repository, CompanyDTO.obj_to_dict, lambda company: company.company_key)

    def _list_page(self, query: dict, repository, to_dict, key_of) -> dict:
        validate_json(query, GET_ADMIN_PAGE_SCHEMA)
        size = page_size(query)
        before_id = self._cursor_id(query.get("cursor"), repository.get_by_key)

        items = repository.list_newest_first(size + 1, before_id)
        return build_page(items, size, to_dict, key_of)

    @staticmethod
    def _cursor_id(cursor: str, find_by_key) -> int:
        if cursor is None:
            return None
        item = find_by_key(cursor)
        if item is None:
            raise InvalidSchema(f"cursor: {cursor} does not point to an existing item")
        return item.id
