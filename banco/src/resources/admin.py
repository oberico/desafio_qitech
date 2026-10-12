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

    def on_get_companies(self, request: Request) -> JSONResponse:
        controller = AdminController(get_context().session)
        page = controller.list_companies(dict(request.query_params))
        return JSONResponse(content=jsonable_encoder(page), status_code=http_status.HTTP_200_OK)

    def on_get_accounts(self, request: Request) -> JSONResponse:
        controller = AdminController(get_context().session)
        page = controller.list_accounts(dict(request.query_params))
        return JSONResponse(content=jsonable_encoder(page), status_code=http_status.HTTP_200_OK)

    def on_get_internal_accounts(self) -> JSONResponse:
        controller = AdminController(get_context().session)
        totals = controller.ledger_totals()
        return JSONResponse(content=jsonable_encoder(totals), status_code=http_status.HTTP_200_OK)
