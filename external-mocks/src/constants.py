import os

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "external-mocks")
MOCK_TIMEOUT_SECONDS = float(os.environ.get("MOCK_TIMEOUT_SECONDS", "30"))

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")

SCENARIO_CONFIRM = "confirm"
SCENARIO_REFUSE = "refuse"
SCENARIO_TIMEOUT = "timeout"
SCENARIO_FLAKY = "flaky"
DEFAULT_SCENARIO = SCENARIO_CONFIRM

FLAKY_FAILURES_BEFORE_CONFIRM = 2
