from fastapi import Body
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ClientController
from database import get_context


class ClientResource:
    def on_post(self, payload: dict = Body(...)) -> JSONResponse:
        controller = ClientController(get_context().session)
        client = controller.create(payload)
        return JSONResponse(content=jsonable_encoder(client), status_code=http_status.HTTP_201_CREATED)
