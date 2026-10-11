from fastapi import Request
from fastapi.responses import JSONResponse

from controllers import TransferController


class TransferResource:
    def __init__(self) -> None:
        self.controller = TransferController()

    async def on_post(self, request: Request) -> JSONResponse:
        outcome = await self.controller.create(await request.body())
        return JSONResponse(status_code=outcome.http_status, content=outcome.body)
