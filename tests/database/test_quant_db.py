import pytest
import os

from quant_toolkit.database.db_default_config import default_logging_info
from quant_toolkit.database.quant_db import QuantDatabaseInteractor


def test_quant_database_interactor_uses_default_login_info():
    db = QuantDatabaseInteractor(is_verbose=False)

    assert db.database_config.database_name == default_logging_info["database_name"]
    assert db.database_config.db_host == default_logging_info["db_host"]
    assert db.database_config.db_port == default_logging_info["db_port"]
    assert db.database_config.db_user == default_logging_info["db_user"]
    assert db.database_config.db_password == default_logging_info["db_password"]
    assert db.database_config.dialect == default_logging_info["dialect"]
    assert db.database_config.driver == default_logging_info["driver"]

    if default_logging_info["is_ssh"]:
        assert db.ssh_config is not None
        assert db.ssh_config.ssh_host == default_logging_info["ssh_host"]
        assert db.ssh_config.ssh_port == default_logging_info["ssh_port"]
        assert db.ssh_config.ssh_user == default_logging_info["ssh_user"]
        assert db.ssh_config.ssh_auth_method == default_logging_info["ssh_auth_method"]
    else:
        assert db.ssh_config is None


def test_quant_database_interactor_requires_is_ssh_key():
    login_info = {
        "database_name": "test_db",
        "db_host": "127.0.0.1",
        "db_port": 3306,
        "db_user": "root",
        "db_password": "",
    }

    with pytest.raises(ValueError, match="Missing required SSH config key: is_ssh"):
        QuantDatabaseInteractor(login_info=login_info, is_verbose=False)


@pytest.mark.integration
def test_quant_database_interactor_default_remote_smoke():
    if os.environ.get("RUN_REMOTE_DB_TEST") != "1":
        pytest.skip("Set RUN_REMOTE_DB_TEST=1 to run remote database smoke test.")

    with QuantDatabaseInteractor(is_verbose=True) as db:
        assert db.ping() is True
