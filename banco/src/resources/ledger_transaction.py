from fastapi import Body, Header
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from constants import IDEMPOTENCY_KEY_MAX_LENGTH
from controllers import LedgerController
from database import get_context


class LedgerTransactionResource:
    def on_post(
        self,
        payload: dict = Body(...),
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=IDEMPOTENCY_KEY_MAX_LENGTH),
    ) -> JSONResponse:
        controller = LedgerController(get_context().session)
        transaction, created = controller.create_transaction(payload, idempotency_key)
        status_code = http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(transaction), status_code=status_code)
