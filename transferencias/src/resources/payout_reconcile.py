from fastapi import Body
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers import PayoutReconcileController
from database import get_context


class PayoutReconcileResource:
    def on_post(self, payload: dict = Body(None)) -> JSONResponse:
        controller = PayoutReconcileController(get_context().session)
        result = controller.run(payload)
        return JSONResponse(content=result, status_code=http_status.HTTP_200_OK)
