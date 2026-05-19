import os

import pytest
from sqlalchemy import text

from quant_toolkit.database.sql_connector import (
    DatabaseConfig,
    SSHConfig,
    SQLDatabaseConnector,
)


@pytest.mark.integration
def test_sql_database_connector_remote_ssh_smoke():
    if os.environ.get("RUN_REMOTE_DB_TEST") != "1":
        pytest.skip("Set RUN_REMOTE_DB_TEST=1 to run remote database smoke test.")

    default_logging_info = {
        # SSH connection info
        "ssh_host": "188.245.87.16",
        "ssh_port": 22,
        "ssh_user": "sif_user_2025",
        "ssh_auth_method": "password",
        "ssh_password": "sif_2025!",

        # Database connection info
        "db_host": "127.0.0.1",
        "db_port": 3306,
        "db_user": "sif_db_ro_2025",
        "db_password": "RO2025!",
        "database_name": "sif_test_db",
    }

    database_config = DatabaseConfig(
        database_name=default_logging_info["database_name"],
        db_host=default_logging_info["db_host"],
        db_port=default_logging_info["db_port"],
        db_user=default_logging_info["db_user"],
        db_password=default_logging_info["db_password"],
        dialect="mysql",
        driver="pymysql",
    )

    ssh_config = SSHConfig(
        ssh_host=default_logging_info["ssh_host"],
        ssh_port=default_logging_info["ssh_port"],
        ssh_user=default_logging_info["ssh_user"],
        ssh_auth_method=default_logging_info["ssh_auth_method"],
        ssh_password=default_logging_info["ssh_password"],
    )

    with SQLDatabaseConnector(
        database_config=database_config,
        ssh_config=ssh_config,
        is_verbose=True,
    ) as db:
        result = db._conn.execute(text("SELECT 1;")).fetchone()

    assert result[0] == 1

