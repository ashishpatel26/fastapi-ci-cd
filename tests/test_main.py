import importlib.util
import sys
from pathlib import Path

MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("main", MAIN_PATH)
main = importlib.util.module_from_spec(SPEC)
sys.modules["main"] = main
SPEC.loader.exec_module(main)


def test_hello_returns_production_message():
    assert main.hello() == {"message": "Hello Production"}