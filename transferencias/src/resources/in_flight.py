from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers import InFlightController
from database import get_context


class InFlightResource:
    def on_get(self, account_key: str) -> JSONResponse:
        controller = InFlightController(get_context().session)
        summary = controller.summarize(account_key)
        return JSONResponse(content=summary, status_code=http_status.HTTP_200_OK)
