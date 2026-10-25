from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as ConnectionPoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from constants import IDEMPOTENCY_KEY_MAX_LENGTH
from errors import InvalidIdempotencyKey, InvalidSchema, MethodNotAllowed, NotFoundRoute, QIException, ServiceBusy
from errors.handlers import qi_exception_to_response
from middlewares import (
    register_admin_auth_middleware,
    register_client_auth_middleware,
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
)
from resources import AdminResource, HealthCheckResource, InFlightResource, PaymentMethodResource, PaymentResource, PayoutFeeResource, PayoutReconcileResource, PayoutResource, ReceiptReconcileResource, SettlementResource
from utils.logger import setup_logging

setup_logging()

application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def handle_qi_exception(request: Request, exception: QIException) -> JSONResponse:
    return qi_exception_to_response(exception)


def handle_request_validation(request: Request, exception: RequestValidationError) -> JSONResponse:
    error = exception.errors()[0]
    reason = f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
    if tuple(error["loc"][:2]) == ("header", "Idempotency-Key"):
        return qi_exception_to_response(InvalidIdempotencyKey(reason, IDEMPOTENCY_KEY_MAX_LENGTH))
    return qi_exception_to_response(InvalidSchema(reason))


def handle_pool_timeout(request: Request, exception: ConnectionPoolTimeout) -> JSONResponse:
    return qi_exception_to_response(ServiceBusy())


ROUTING_ERRORS = {404: NotFoundRoute, 405: MethodNotAllowed}


async def handle_http_exception(request: Request, exception: StarletteHTTPException) -> JSONResponse:
    error_class = ROUTING_ERRORS.get(exception.status_code)
    if error_class is None:
        return await http_exception_handler(request, exception)
    return qi_exception_to_response(error_class(), exception.headers)


application.add_exception_handler(StarletteHTTPException, handle_http_exception)
application.add_exception_handler(QIException, handle_qi_exception)
application.add_exception_handler(RequestValidationError, handle_request_validation)
application.add_exception_handler(ConnectionPoolTimeout, handle_pool_timeout)

register_client_auth_middleware(application)
register_admin_auth_middleware(application)
register_session_manager_middleware(application)
register_internal_token_middleware(application)
register_request_logger_middleware(application)
register_request_context_middleware(application)

admin_resource = AdminResource()
health_check_resource = HealthCheckResource()
in_flight_resource = InFlightResource()
payment_resource = PaymentResource()
payment_method_resource = PaymentMethodResource()
payout_fee_resource = PayoutFeeResource()
payout_resource = PayoutResource()
payout_reconcile_resource = PayoutReconcileResource()
receipt_reconcile_resource = ReceiptReconcileResource()
settlement_resource = SettlementResource()

application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
application.add_api_route("/health_check", health_check_resource.on_get_health_check, methods=["GET"])
application.add_api_route("/payments", payment_resource.on_post, methods=["POST"])
application.add_api_route("/payments", payment_resource.on_get, methods=["GET"])
application.add_api_route("/payments/{payment_key}", payment_resource.on_get_by_key, methods=["GET"])
application.add_api_route("/payments/{payment_key}/refund", payment_resource.on_post_refund, methods=["POST"])
application.add_api_route("/payouts", payout_resource.on_post, methods=["POST"])
application.add_api_route("/payouts/{payout_key}", payout_resource.on_get_by_key, methods=["GET"])
application.add_api_route("/internal/accounts/{account_key}/in-flight", in_flight_resource.on_get, methods=["GET"])
application.add_api_route("/internal/payouts/reconcile", payout_reconcile_resource.on_post, methods=["POST"])
application.add_api_route("/internal/receipts/reconcile", receipt_reconcile_resource.on_post, methods=["POST"])
application.add_api_route("/internal/settlements", settlement_resource.on_post, methods=["POST"])
application.add_api_route("/internal/payment-methods/{method}", payment_method_resource.on_put, methods=["PUT"])
application.add_api_route("/internal/payout-fee", payout_fee_resource.on_put, methods=["PUT"])
application.add_api_route("/admin/payments", admin_resource.on_get_payments, methods=["GET"])
