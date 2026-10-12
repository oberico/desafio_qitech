from fastapi import Body
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PaymentMethodController
from database import get_context


class PaymentMethodResource:
    def on_put(self, method: str, payload: dict = Body(None)) -> JSONResponse:
        controller = PaymentMethodController(get_context().session)
        method_terms, created = controller.change_terms(method, payload)
        status_code = http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(method_terms), status_code=status_code)
