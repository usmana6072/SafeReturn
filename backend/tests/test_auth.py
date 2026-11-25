# Minimal stub for test_auth used by integration tests
# Provides dummy authentication data sufficient for import.

# Base URL for test requests (not used in guards tests)
ORIGIN = "http://localhost"


def claims(*args, **kwargs):
    """Return an empty claims dict. Adjust as needed for specific tests."""
    return {}


def keyset(*args, **kwargs):
    """Return a dummy keyset placeholder."""
    return {}


def signed(*args, **kwargs):
    """Return a dummy signed token placeholder."""
    return {}
