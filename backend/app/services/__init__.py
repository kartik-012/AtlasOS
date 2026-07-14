"""
AtlasOS Services Package.

Service classes contain all business logic. They orchestrate repositories,
enforce business rules, and are injected into API routes via FastAPI DI.

Services NEVER access the database directly — they always go through
repository instances.
"""
