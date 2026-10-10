from fastapi import Body, Header
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PaymentController
from database import get_context


class PaymentResource:
    def on_post(
        self,
        payload: dict = Body(...),
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=50),
    ) -> JSONResponse:
        controller = PaymentController(get_context().session)
        payment, created = controller.create(payload, idempotency_key)
        status_code = http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(payment), status_code=status_code)

    def on_get_by_key(self, payment_key: str) -> JSONResponse:
        controller = PaymentController(get_context().session)
        payment = controller.get_by_key(payment_key)
        return JSONResponse(content=jsonable_encoder(payment), status_code=http_status.HTTP_200_OK)
