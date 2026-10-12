from fastapi import Body, Header, Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PayoutController
from database import get_context


class PayoutResource:
    def on_post(
        self,
        request: Request,
        payload: dict = Body(...),
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=50),
    ) -> JSONResponse:
        controller = PayoutController(get_context().session)
        payout, created = controller.create(payload, idempotency_key, request.state.companies)
        status_code = http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(payout), status_code=status_code)

    def on_get_by_key(self, request: Request, payout_key: str) -> JSONResponse:
        controller = PayoutController(get_context().session)
        payout = controller.get_by_key(payout_key, request.state.companies)
        return JSONResponse(content=jsonable_encoder(payout), status_code=http_status.HTTP_200_OK)
