# tests/conftest.py
import os
import sys
import logging

import pytest

from braille_translator.translator import BrailleTranslator

# ----------------------------------------------------------------------
# Ensure project root is on PYTHONPATH so imports work
# ----------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ----------------------------------------------------------------------
# Pytest configuration: logging to file
# ----------------------------------------------------------------------
def pytest_configure(config):
    log_dir = os.path.join(PROJECT_ROOT, "tests", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "test_results.log")

    logging.basicConfig(
        filename=log_file,
        filemode='w',
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s:%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Suppress overly verbose logs from pytest internals
    logging.getLogger("pytest").setLevel(logging.WARNING)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    After each test, append pass/fail status and last error line (if any)
    to the log file.
    """
    outcome = yield
    rep = outcome.get_result()
    logger = logging.getLogger("pytest")

    if rep.when == "call":
        status = "PASSED" if rep.passed else "FAILED"
        logger.info(f"Test {item.name}: {status}")
        if rep.failed and rep.longrepr:
            # log only the last line of the failure traceback
            last_line = rep.longreprtext.splitlines()[-1]
            logger.error(f"  {last_line}")

# ----------------------------------------------------------------------
# Common fixtures for tests
# ----------------------------------------------------------------------
@pytest.fixture(scope="session")
def translator():
    """
    Reuse a single BrailleTranslator instance across tests.
    """
    return BrailleTranslator()

@pytest.fixture(scope="session")
def sample_texts():
    """
    Provide sample texts for English, Korean, and mixed-language tests.
    """
    return {
        "english": ["and", "hello", "the", "zigzag"],
        "korean": ["안녕", "한글", "감사합니다"],
        "mixed": ["Hello 안녕 123!", "Test 테스트, 42번!"],
    }