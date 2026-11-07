"""Integration tests against the DEV environment.

These tests run against REAL DEV systems (SAP SQL Server, Service Layer,
PostgreSQL event store) and are skipped unless the corresponding environment
variables are set. They are marked `integration` so they can be excluded from
the fast unit-test run:

    pytest -m "not integration"          # unit tests only (CI default)
    pytest -m integration                # integration tests only (nightly cron)

All SAP access here is read-only (MSSQL SELECT) or DRY_RUN (Service Layer).
No real SAP writes are ever performed by these tests.
"""
