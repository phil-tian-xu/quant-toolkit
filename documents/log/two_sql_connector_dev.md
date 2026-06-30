# SQL Connector Review Notes

## Fixed Correctness Issues

- Removed unused `if_exists` parameter from `drop_table`.
- Added `mode` type validation in `write_dataframe`.
- Added positive integer validation for `chunksize` in `write_dataframe`.
- Added `where_clause` type validation in `fetch_table`.
- Reordered `table_name` validation so type checks happen before empty-value checks in:
  - `fetch_table`
  - `delete_rows`
  - `truncate_table`

## Accepted Design Choice

- `write_dataframe(mode="upsert")` returns the database affected row count.
- Other write modes return `len(df)`.
- This is intentional and documented because MySQL affected row count can differ for inserted vs updated rows.

## Remaining Future Polish

- Table and column names are interpolated directly into SQL.
- This is acceptable for trusted internal use for now.
- Later, we may add identifier validation/quoting helpers if needed.\

