import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SERVICES = ["banco", "transferencias"]


def pytest_cmdline_main(config):
    invoked_from_root = Path(config.invocation_params.dir).resolve() == ROOT.resolve()
    if not invoked_from_root or config.invocation_params.args:
        return None
    exit_codes = [
        subprocess.call([sys.executable, "-m", "pytest"], cwd=ROOT / service)
        for service in SERVICES
    ]
    return max(exit_codes)
