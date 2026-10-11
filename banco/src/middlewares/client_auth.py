from fastapi import FastAPI, Request
from starlette.routing import Match

from constants import INTERNAL_ROUTE_PREFIXES, PUBLIC_ROUTES
from controllers import ClientController
from database import get_context
from errors import QIException
from errors.handlers import qi_exception_to_response

BEARER_PREFIX = "Bearer "


def bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith(BEARER_PREFIX):
        return None
    return authorization[len(BEARER_PREFIX):].strip() or None


def requires_client_token(application: FastAPI, request: Request) -> bool:
    if request.url.path.startswith(INTERNAL_ROUTE_PREFIXES):
        return False
    for route in application.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return (request.method, route.path) not in PUBLIC_ROUTES
    return False


def register_client_auth_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def authenticate_client(request: Request, call_next):
        if not requires_client_token(application, request):
            return await call_next(request)

        try:
            client = ClientController(get_context().session).authenticate(bearer_token(request))
        except QIException as exception:
            return qi_exception_to_response(exception)

        request.state.client_id = client.id
        return await call_next(request)
