from fastapi import Body
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers import SettlementController
from database import get_context


class SettlementResource:
    def on_post(self, payload: dict = Body(None)) -> JSONResponse:
        controller = SettlementController(get_context().session)
        result = controller.run(payload)
        return JSONResponse(content=result, status_code=http_status.HTTP_200_OK)
