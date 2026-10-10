from fastapi import FastAPI

from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
)
from resources import HealthCheckResource
from utils.logger import setup_logging

setup_logging()

application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

register_internal_token_middleware(application)
register_request_logger_middleware(application)
register_request_context_middleware(application)

health_check_resource = HealthCheckResource()

application.add_api_route("/", health_check_resource.on_get, methods=["GET"])
application.add_api_route("/health_check", health_check_resource.on_get, methods=["GET"])
