import os

import pytest
from sqlalchemy import text

from quant_toolkit.database.sql_connector import (
    DatabaseConfig,
    SQLDatabaseConnector,
)

@pytest.mark.integration
def test_sql_database_connector_local_smoke():
    if os.environ.get("RUN_LOCAL_DB_TEST") != "1":
        pytest.skip("Set RUN_LOCAL_DB_TEST=1 to run local database smoke test.")

    database_config = DatabaseConfig(
        database_name=os.environ.get("LOCAL_DB_NAME", "quant_datahub"),
        db_host=os.environ.get("LOCAL_DB_HOST", "127.0.0.1"),
        db_port=int(os.environ.get("LOCAL_DB_PORT", 3306)),
        db_user=os.environ.get("LOCAL_DB_USER", "root"),
        db_password=os.environ.get("LOCAL_DB_PASSWORD", ""),
        dialect="mysql",
        driver="pymysql",
    )

    with SQLDatabaseConnector(
        database_config=database_config,
        ssh_config=None,
        is_verbose=True,
    ) as db:
        result = db.execute("SELECT 1;").fetchone()

    assert result[0] == 1

