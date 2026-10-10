from fastapi import Body, Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import CompanyController
from database import get_context


class CompanyResource:
    def on_post(self, request: Request, payload: dict = Body(...)) -> JSONResponse:
        controller = CompanyController(get_context().session)
        company = controller.create(payload, request.state.client_id)
        return JSONResponse(content=jsonable_encoder(company), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, request: Request, company_key: str) -> JSONResponse:
        controller = CompanyController(get_context().session)
        company = controller.get_by_key(company_key, request.state.client_id)
        return JSONResponse(content=jsonable_encoder(company), status_code=http_status.HTTP_200_OK)
