"""Root conftest.py for pytest configuration.

This file configures pytest options and hooks for E2E tests.
"""


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run E2E tests that require Claude Code CLI",
    )


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests that use actual Claude Code (skipped by default)",
    )


def pytest_collection_modifyitems(config, items):
    """Modify E2E test collection to skip by default."""
    import pytest

    if not config.getoption("--run-e2e", default=False):
        skip_e2e = pytest.mark.skip(reason="E2E tests require --run-e2e flag")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)
