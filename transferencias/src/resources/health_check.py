from fastapi import Response, status
from fastapi.responses import JSONResponse


class HealthCheckResource:
    def on_get_home(self) -> JSONResponse:
        home = {"service": "transferencias"}
        return JSONResponse(content=home, status_code=status.HTTP_200_OK)

    def on_get_health_check(self) -> Response:
        return Response(status_code=status.HTTP_204_NO_CONTENT)