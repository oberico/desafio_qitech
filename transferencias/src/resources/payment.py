from fastapi import Header
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PaymentController
from utils.schema_handler import SchemaHandler


class PaymentResource:
    @SchemaHandler.validate("post_payment.json")
    def on_post(
        self,
        payload: dict,
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=80),
    ) -> JSONResponse:
        controller = PaymentController()
        payment, created = controller.create(payload, idempotency_key)

        if created:
            status_code = http_status.HTTP_201_CREATED
        else:
            status_code = http_status.HTTP_200_OK

        return JSONResponse(content=jsonable_encoder(payment), status_code=status_code)

    def on_get_by_key(self, payment_key: str) -> JSONResponse:
        controller = PaymentController()
        payment = controller.get_by_key(payment_key)

        return JSONResponse(
            content=jsonable_encoder(payment),
            status_code=http_status.HTTP_200_OK,
        )
