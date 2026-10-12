import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SERVICES = ["banco", "transferencias", "external-mocks"]


def targets_a_path(args) -> bool:
    return any((ROOT / arg.split("::")[0]).exists() for arg in args if not arg.startswith("-"))


def pytest_cmdline_main(config):
    invoked_from_root = Path(config.invocation_params.dir).resolve() == ROOT.resolve()
    args = list(config.invocation_params.args)
    if not invoked_from_root or targets_a_path(args):
        return None
    exit_codes = []
    for service in SERVICES:
        print(f"\n=== {service} ===", flush=True)
        exit_codes.append(subprocess.call([sys.executable, "-m", "pytest", *args], cwd=ROOT / service))
    return max(exit_codes)
