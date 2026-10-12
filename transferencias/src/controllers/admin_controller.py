import os

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import PaymentDTO
from repositories import PaymentRepository
from utils.cursor import decode_cursor, encode_cursor
from utils.pagination import build_page, page_size
from utils.schema_handler import validate_json

GET_ADMIN_PAYMENTS_SCHEMA = os.path.join(SCHEMAS_DIR, "get_admin_payments.json")


class AdminController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.payment_repository = PaymentRepository(session)

    def list_payments(self, query: dict) -> dict:
        validate_json(query, GET_ADMIN_PAYMENTS_SCHEMA, root="query")
        size = page_size(query)
        before_id = decode_cursor(query["cursor"]) if "cursor" in query else None

        payments = self.payment_repository.list_all_newest_first(
            size + 1, before_id, query.get("status"), query.get("company_key")
        )
        return build_page(payments, size, PaymentDTO.obj_to_dict, lambda payment: encode_cursor(payment.id))
