# Database Development Plan

Last updated: 2026-05-19

## Scope

The database feature in `quant-toolkit` should provide convenient, safe access to the new quant database for research and data analysis workflows.

For now, the project should include two layers:

1. A generic database connector.
2. A project/database-specific interactor.

Privileged database administration features should be developed later in a separate package.

## Architecture

```text
Generic database connector
  -> SQLAlchemy connection handling
  -> direct or SSH-tunneled access
  -> common query/DataFrame helpers

Project database interactor
  -> new quant database schema-aware helpers
  -> universe, mapping, metadata, and time-series access
  -> mostly read-oriented user APIs

Admin/manager layer
  -> out of scope for quant-toolkit
  -> future independent package
```

## Generic Connector

The generic connector should replace the old `SQLAlchemyInteractor` idea with a cleaner implementation.

Expected responsibilities:

- Create SQLAlchemy engines.
- Support direct database connections.
- Support optional SSH tunnel connections.
- Manage connection lifecycle with `connect()`, `close()`, and context manager usage.
- Fetch query results as pandas DataFrames.
- Execute parameterized SQL statements.
- Insert pandas DataFrames into database tables.
- Provide basic inspection helpers such as table existence and column listing.
- Provide clear logging and error messages.

This layer should not contain any database-specific business logic.

## Project Database Interactor

The project-specific interactor should sit on top of the generic connector.

Expected responsibilities:

- Know the new quant database table structure.
- Provide convenient methods for common research queries.
- Handle instrument/security mapping if the new database uses internal ids.
- Fetch time-series data.
- Fetch metadata.
- Fetch universe or instrument lists.

This layer should avoid destructive operations by default.

## Out Of Scope

The following should not be part of the first `quant-toolkit` database implementation:

- Dropping tables.
- Altering schemas.
- Deleting production data.
- Database migrations.
- Pipeline orchestration.
- Cloud database maintenance.
- Admin-only workflows.

These can be developed later in a separate higher-access package.

## First Milestone

TODO
