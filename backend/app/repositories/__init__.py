"""
AtlasOS Repositories Package.

Repository classes provide a clean abstraction over SQLAlchemy ORM
operations. All database access in the application MUST go through
a repository — never direct ORM queries in services or routes.

This enforces:
  - Single Responsibility: Repositories handle data access only.
  - Testability: Repositories can be mocked in service-layer tests.
  - Consistency: All queries follow the same patterns.
"""
