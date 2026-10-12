import hmac

from fastapi import FastAPI, Request

from constants import ADMIN_ROUTE_PREFIX, ADMIN_TOKEN
from controllers import ClientController
from database import get_context
from errors import AdminForbidden, QIException
from errors.handlers import qi_exception_to_response
from utils.token import bearer_token


def is_admin_token(received_token: str) -> bool:
    if not ADMIN_TOKEN or not received_token:
        return False
    return hmac.compare_digest(received_token.encode("utf-8"), ADMIN_TOKEN.encode("utf-8"))


def register_admin_auth_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def authenticate_admin(request: Request, call_next):
        if not request.url.path.startswith(ADMIN_ROUTE_PREFIX):
            return await call_next(request)

        token = bearer_token(request.headers.get("Authorization"))
        if is_admin_token(token):
            return await call_next(request)

        try:
            ClientController(get_context().session).authenticate(token)
        except QIException as exception:
            return qi_exception_to_response(exception)
        return qi_exception_to_response(AdminForbidden())
