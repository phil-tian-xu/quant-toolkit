from quant_toolkit.database.db_default_config import default_logging_info
from quant_toolkit.database.sql_connector import SQLDatabaseConnector, DatabaseConfig, SSHConfig


class QuantDatabaseInteractor(SQLDatabaseConnector):
    verbose_prefix = "[quant-toolkit] Quant Database Info:"
    error_prefix = "[quant-toolkit] Quant Database Error:"

    def __init__(
            self,
            login_info: dict = None,
            is_verbose: bool = True,
            engine_options: dict = None,
    ):
        if login_info is None:
            login_info = default_logging_info

        database_config = self._load_quant_database_config(login_info)
        ssh_config = self._load_quant_ssh_config(login_info)

        super().__init__(
            database_config=database_config,
            ssh_config=ssh_config,
            is_verbose=is_verbose,
            engine_options=engine_options,
        )

    @classmethod
    def _load_quant_database_config(cls, login_info: dict) -> DatabaseConfig:
        required_keys = ["database_name", "db_host", "db_port", "db_user"]

        for key in required_keys:
            if key not in login_info:
                raise ValueError(
                    f"{cls.error_prefix} Missing required database config key: {key}"
                )
        return DatabaseConfig(
            database_name=login_info["database_name"],
            db_host=login_info["db_host"],
            db_port=login_info["db_port"],
            db_user=login_info["db_user"],
            db_password=login_info.get("db_password", ""),
            dialect=login_info.get("dialect", "mysql"),
            driver=login_info.get("driver", "pymysql"),
        )

    @classmethod
    def _load_quant_ssh_config(cls, login_info: dict) -> SSHConfig | None:
        if "is_ssh" not in login_info:
            raise ValueError(
                f"{cls.error_prefix} Missing required SSH config key: is_ssh"
            )
        is_ssh = login_info.get("is_ssh")

        if not is_ssh:
            return None

        required_keys = ["ssh_host", "ssh_user"]
        for key in required_keys:
            if key not in login_info:
                raise ValueError(
                    f"{cls.error_prefix} Missing required SSH config key: {key}"
                )
        return SSHConfig(
            ssh_host=login_info["ssh_host"],
            ssh_port=login_info.get("ssh_port", 22),
            ssh_user=login_info["ssh_user"],
            ssh_auth_method=login_info.get("ssh_auth_method", "ssh_key_pairs"),
            ssh_password=login_info.get("ssh_password"),
            ssh_key_path=login_info.get("ssh_key_path", "~/.ssh/id_rsa"),
            ssh_private_key_password=login_info.get("ssh_private_key_password"),
            local_bind_host=login_info.get("local_bind_host", "127.0.0.1"),
            local_bind_port=login_info.get("local_bind_port", 0),
        )

    def get_universe(self):
        ...

    def get_instrument_mapping(self):
        ...

    def select_time_series(self):
        ...

    def select_metadata(self):
        ...