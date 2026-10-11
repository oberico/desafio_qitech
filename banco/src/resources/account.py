from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountController
from database import get_context


class AccountResource:
    def on_post(self, request: Request, company_key: str) -> JSONResponse:
        controller = AccountController(get_context().session)
        account = controller.open(company_key, request.state.client_id)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, request: Request, account_key: str) -> JSONResponse:
        controller = AccountController(get_context().session)
        account = controller.get_by_key(account_key, request.state.client_id)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)

    def on_post_close(self, request: Request, account_key: str) -> JSONResponse:
        controller = AccountController(get_context().session)
        account = controller.close(account_key, request.state.client_id)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)

    def on_get_internal(self) -> JSONResponse:
        controller = AccountController(get_context().session)
        accounts = controller.list_internal()
        return JSONResponse(content=jsonable_encoder(accounts), status_code=http_status.HTTP_200_OK)
