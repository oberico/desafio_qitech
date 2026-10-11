from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ClientController
from database import get_context
from utils.token import bearer_token


class AuthResource:
    def on_get_me(self, request: Request) -> JSONResponse:
        controller = ClientController(get_context().session)
        identity = controller.get_identity(bearer_token(request.headers.get("Authorization")))
        return JSONResponse(content=jsonable_encoder(identity), status_code=http_status.HTTP_200_OK)
