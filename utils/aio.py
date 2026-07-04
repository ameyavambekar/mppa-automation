"""AIO Tests integration helpers — tag a pytest test with its AIO case key
so the result can be posted back to AIO via REST."""

import functools


def aio_case(key: str):
    """Tag a test with its AIO Tests case key (e.g. 'KAN-TC-7').

    The key is stored on the wrapped function as `_aio_case_key`. A hook in
    conftest.py reads it during collection and adds it to the test's
    `user_properties`, which surfaces it in the JUnit XML and is available
    to the `pytest_runtest_makereport` hook for REST upload to AIO.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._aio_case_key = key
        return wrapper
    return decorator
