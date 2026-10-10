from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errors import InvalidSchema, QIException
from errors.handlers import qi_exception_to_response
from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
)
from resources import HealthCheckResource, PaymentResource
from utils.logger import setup_logging

setup_logging()

application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def handle_qi_exception(request: Request, exception: QIException) -> JSONResponse:
    return qi_exception_to_response(exception)


def handle_request_validation(request: Request, exception: RequestValidationError) -> JSONResponse:
    return qi_exception_to_response(InvalidSchema(str(exception.errors()[0]["loc"])))


application.add_exception_handler(QIException, handle_qi_exception)
application.add_exception_handler(RequestValidationError, handle_request_validation)

register_session_manager_middleware(application)
register_internal_token_middleware(application)
register_request_logger_middleware(application)
register_request_context_middleware(application)

health_check_resource = HealthCheckResource()
payment_resource = PaymentResource()

application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
application.add_api_route("/health_check", health_check_resource.on_get_health_check, methods=["GET"])
application.add_api_route("/payments", payment_resource.on_post, methods=["POST"])
application.add_api_route("/payments/{payment_key}", payment_resource.on_get_by_key, methods=["GET"])
