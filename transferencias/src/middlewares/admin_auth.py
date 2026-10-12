import hmac

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

from connectors import BankConnector
from constants import ADMIN_ROUTE_PREFIX, ADMIN_TOKEN
from errors import AdminForbidden, InvalidClientToken, QIException
from errors.handlers import qi_exception_to_response
from middlewares.client_auth import bearer_token


def is_admin_token(received_token: str) -> bool:
    if not ADMIN_TOKEN or not received_token:
        return False
    return hmac.compare_digest(received_token.encode("utf-8"), ADMIN_TOKEN.encode("utf-8"))


def register_admin_auth_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def authenticate_admin(request: Request, call_next):
        if not request.url.path.startswith(ADMIN_ROUTE_PREFIX):
            return await call_next(request)

        token = bearer_token(request)
        if is_admin_token(token):
            return await call_next(request)

        if token is None:
            return qi_exception_to_response(InvalidClientToken())

        try:
            identity = await run_in_threadpool(BankConnector().get_client_identity, token)
        except QIException as exception:
            return qi_exception_to_response(exception)

        if identity is None:
            return qi_exception_to_response(InvalidClientToken())
        return qi_exception_to_response(AdminForbidden())
