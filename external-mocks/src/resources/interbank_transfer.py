from fastapi import Request
from fastapi.responses import JSONResponse

from controllers import InterbankTransferController


class InterbankTransferResource:
    def __init__(self) -> None:
        self.controller = InterbankTransferController()

    async def on_post(self, request: Request) -> JSONResponse:
        outcome = await self.controller.create(await request.body())
        return JSONResponse(status_code=outcome.http_status, content=outcome.body)
