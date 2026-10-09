from fastapi import status as http_status
from fastapi.responses import JSONResponse

from controllers.health_check_controller import HealthCheckController


class HealthCheckResource:
    def on_get(self) -> JSONResponse:
        controller = HealthCheckController()
        return JSONResponse(content=controller.check(), status_code=http_status.HTTP_200_OK)
