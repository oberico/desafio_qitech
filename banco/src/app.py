from fastapi import FastAPI

from resources import HealthCheckResource

application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

health_check_resource = HealthCheckResource()

application.add_api_route("/", health_check_resource.on_get, methods=["GET"])
application.add_api_route("/health_check", health_check_resource.on_get, methods=["GET"])
