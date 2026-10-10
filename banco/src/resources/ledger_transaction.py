from fastapi import Body
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers.ledger_controller import LedgerController


class LedgerTransactionResource:
    def on_post(self, payload: dict = Body(...)) -> JSONResponse:
        controller = LedgerController()
        transaction = controller.create_transaction(payload)
        return JSONResponse(content=transaction, status_code=http_status.HTTP_201_CREATED)