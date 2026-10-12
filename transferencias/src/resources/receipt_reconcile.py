from fastapi import Body
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers import ReceiptReconcileController
from database import get_context


class ReceiptReconcileResource:
    def on_post(self, payload: dict = Body(None)) -> JSONResponse:
        controller = ReceiptReconcileController(get_context().session)
        result = controller.run(payload)
        return JSONResponse(content=result, status_code=http_status.HTTP_200_OK)
