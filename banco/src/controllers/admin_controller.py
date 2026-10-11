import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import AdminClientDTO
from errors import InvalidSchema
from repositories import ClientRepository
from utils.pagination import build_page, page_size
from utils.schema_handler import validate_json

GET_ADMIN_CLIENTS_SCHEMA = os.path.join(SCHEMAS_DIR, "get_admin_clients.json")


class AdminController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.client_repository = ClientRepository(session)

    def list_clients(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_CLIENTS_SCHEMA)
        size = page_size(query)
        before_id = self._cursor_id(query.get("cursor"), self.client_repository.get_by_key)

        clients = self.client_repository.list_newest_first(size + 1, before_id)
        return build_page(clients, size, AdminClientDTO.obj_to_dict, lambda client: client.client_key)

    @staticmethod
    def _cursor_id(cursor: str, find_by_key) -> int:
        if cursor is None:
            return None
        item = find_by_key(cursor)
        if item is None:
            raise InvalidSchema(f"cursor: {cursor} does not point to an existing item")
        return item.id
