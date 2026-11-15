"""
Test marking for the database (D46). One helper for the grader tests and the app tests.

    from _db import needs_db

    @needs_db
    def test_something(self): ...      # a test, or a whole TestCase class

A marked test is skipped ONLY when the environment variable SKIP_DB_TESTS=1 is set (CI sets it). The reason shown
is "needs the full SMARD database". Without that variable nothing is skipped: the tests run as before and fail
if the database is down, so a local run can never pass by accident.
"""

import os
import unittest

SKIP_REASON = "needs the full SMARD database"


def needs_db(obj):
    """Decorator for a test method or a TestCase class that needs the database or the loaded SMARD data."""
    if os.environ.get("SKIP_DB_TESTS") == "1":
        return unittest.skip(SKIP_REASON)(obj)
    return obj
