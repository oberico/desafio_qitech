from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errors import InvalidSchema, QIException
from errors.handlers import qi_exception_to_response
from middlewares.session_middleware import register_session_middleware
from resources import HealthCheckResource, PaymentResource

application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def handle_qi_exception(request: Request, exception: QIException) -> JSONResponse:
    return qi_exception_to_response(exception)


def handle_request_validation(request: Request, exception: RequestValidationError) -> JSONResponse:
    return qi_exception_to_response(InvalidSchema(str(exception.errors()[0]["loc"])))


application.add_exception_handler(QIException, handle_qi_exception)
application.add_exception_handler(RequestValidationError, handle_request_validation)
register_session_middleware(application)

health_check_resource = HealthCheckResource()
payment_resource = PaymentResource()

application.add_api_route("/", health_check_resource.on_get, methods=["GET"])
application.add_api_route("/health_check", health_check_resource.on_get, methods=["GET"])
application.add_api_route("/payments", payment_resource.on_post, methods=["POST"])
application.add_api_route("/payments/{payment_key}", payment_resource.on_get_by_key, methods=["GET"])
