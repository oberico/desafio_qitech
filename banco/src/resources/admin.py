from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AdminController
from database import get_context


class AdminResource:
    def on_get_clients(self, request: Request) -> JSONResponse:
        controller = AdminController(get_context().session)
        page = controller.list_clients(dict(request.query_params))
        return JSONResponse(content=jsonable_encoder(page), status_code=http_status.HTTP_200_OK)
