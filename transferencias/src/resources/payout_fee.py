from fastapi import Body
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PayoutFeeController
from database import get_context


class PayoutFeeResource:
    def on_put(self, payload: dict = Body(None)) -> JSONResponse:
        controller = PayoutFeeController(get_context().session)
        fee, created = controller.change_fee(payload)
        status_code = http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(fee), status_code=status_code)
