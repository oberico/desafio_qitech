from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.routing import Match

from connectors import BankConnector
from constants import BYPASS_ENDPOINTS, INTERNAL_ROUTE_PREFIX
from errors import InvalidClientToken, QIException
from errors.handlers import qi_exception_to_response

BEARER_PREFIX = "Bearer "


def bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith(BEARER_PREFIX):
        return None
    return authorization[len(BEARER_PREFIX):].strip() or None


def requires_client_token(application: FastAPI, request: Request) -> bool:
    if request.url.path.startswith(INTERNAL_ROUTE_PREFIX) or request.url.path in BYPASS_ENDPOINTS:
        return False
    return any(route.matches(request.scope)[0] == Match.FULL for route in application.router.routes)


def register_client_auth_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def authenticate_client(request: Request, call_next):
        if not requires_client_token(application, request):
            return await call_next(request)

        token = bearer_token(request)
        if token is None:
            return qi_exception_to_response(InvalidClientToken())

        try:
            identity = await run_in_threadpool(BankConnector().get_client_identity, token)
        except QIException as exception:
            return qi_exception_to_response(exception)

        if identity is None:
            return qi_exception_to_response(InvalidClientToken())

        request.state.client_key = identity["client_key"]
        return await call_next(request)
