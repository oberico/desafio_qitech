from fastapi import Body, Header
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers.ledger_controller import LedgerController


class LedgerTransactionResource:
    def on_post(self, payload: dict = Body(...), 
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=100),
    ) -> JSONResponse:
        controller = LedgerController()
        transaction = controller.create_transaction(payload)
        return JSONResponse(content=transaction, status_code=http_status.HTTP_201_CREATED)