import logging
import urllib.parse
from dataclasses import dataclass
from quant_toolkit.constants import PACKAGE_PREFIX
from time import sleep
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, exc
from sshtunnel import SSHTunnelForwarder
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    database_name: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    dialect: str = "mysql"
    driver: str = "pymysql"


@dataclass
class SSHConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_auth_method: str = "ssh_key_pairs"
    ssh_password: str = None
    ssh_key_path: str = "~/.ssh/id_rsa"
    ssh_private_key_password: str = None
    local_bind_host: str = "127.0.0.1"
    local_bind_port: int = 0


class SQLDatabaseConnector:
    verbose_prefix = f"{PACKAGE_PREFIX} SQL Database Connector Info: "

    def __init__(
        self,
        database_config: DatabaseConfig,
        ssh_config: SSHConfig = None,
        is_verbose: bool = True,
        engine_options: dict = None,
    ):
        self.database_config = database_config
        self.ssh_config = ssh_config
        self.is_verbose = is_verbose
        self.engine_options = engine_options or {}

        self._engine = None
        self._conn = None
        self._ssh_tunnel = None
        self._connection_url = None

        self._validate_config()

    def __enter__(self) -> "SQLDatabaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def is_connected(self) -> bool:
        return self._conn is not None and not self._conn.closed

    def connect(self, retries: int = 3, retry_delay: int = 2):
        if self.is_connected():
            return

        try:
            if self.ssh_config is not None and self._ssh_tunnel is None:
                self._start_ssh_tunnel()

            if self._engine is None:
                self._connection_url = self._build_connection_url()
                self._engine = create_engine(self._connection_url, **self.engine_options)
                self._verbose("SQLAlchemy engine created.")

            for attempt in range(1, retries + 1):
                try:
                    self._conn = self._engine.connect()
                    self._verbose(f"Connected to database successfully. Attempt {attempt}.")
                    return
                except exc.SQLAlchemyError as err:
                    self._verbose(f"Connection attempt {attempt} failed: {err}")

                    if attempt < retries:
                        sleep(retry_delay)
                    else:
                        raise

        except Exception as err:
            self._verbose(f"Database connection setup failed: {err}")
            self.close()
            raise

    def close(self, dispose_engine: bool = True, stop_ssh_tunnel: bool = True):
        if self._conn is not None:
            if not self._conn.closed:
                self._conn.close()
                self._verbose("Database connection closed.")
            self._conn = None

        if dispose_engine and self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._verbose("SQLAlchemy engine disposed.")

        if stop_ssh_tunnel and self._ssh_tunnel is not None:
            self._ssh_tunnel.stop()
            self._ssh_tunnel = None
            self._verbose("SSH tunnel stopped.")

    def _start_ssh_tunnel(self):
        if self.ssh_config is None:
            return

        if self._ssh_tunnel is not None:
            return

        ssh_key_path = None
        if self.ssh_config.ssh_key_path:
            ssh_key_path = str(Path(self.ssh_config.ssh_key_path).expanduser())

        ssh_kwargs = {
            "ssh_username": self.ssh_config.ssh_user,
            "remote_bind_address": (
                self.database_config.db_host,
                self.database_config.db_port,
            ),
            "local_bind_address": (
                self.ssh_config.local_bind_host,
                self.ssh_config.local_bind_port,
            ),
            "set_keepalive": 30,
        }

        if self.ssh_config.ssh_auth_method == "ssh_key_pairs":
            ssh_kwargs["ssh_pkey"] = ssh_key_path

            if self.ssh_config.ssh_private_key_password:
                ssh_kwargs["ssh_private_key_password"] = (
                    self.ssh_config.ssh_private_key_password
                )

        elif self.ssh_config.ssh_auth_method == "password":
            ssh_kwargs["ssh_password"] = self.ssh_config.ssh_password
        else:
            raise ValueError()

        self._ssh_tunnel = SSHTunnelForwarder(
            (self.ssh_config.ssh_host, self.ssh_config.ssh_port),
            **ssh_kwargs,
        )

        try:
            self._ssh_tunnel.start()
            self._verbose(
                f"SSH tunnel started on "
                f"{self.ssh_config.local_bind_host}:{self._ssh_tunnel.local_bind_port}."
            )
        except Exception:
            self._ssh_tunnel = None
            raise

    def _build_connection_url(self):
        if self.ssh_config is not None:
            if self._ssh_tunnel is None:
                raise RuntimeError("SSH tunnel must be started before building connection URL.")
            host = self.ssh_config.local_bind_host
            port = self._ssh_tunnel.local_bind_port
        else:
            host = self.database_config.db_host
            port = self.database_config.db_port

        if self.database_config.db_password:
            password = urllib.parse.quote_plus(self.database_config.db_password)
            user_part = f"{self.database_config.db_user}:{password}"
        else:
            user_part = self.database_config.db_user

        return (
            f"{self.database_config.dialect}+{self.database_config.driver}://"
            f"{user_part}@{host}:{port}/{self.database_config.database_name}"
        )

    def _verbose(self, message: str):
        logger.info(message)

        if self.is_verbose:
            print(f"{self.verbose_prefix}{message}")

    def _validate_config(self):
        if not isinstance(self.database_config, DatabaseConfig):
            raise TypeError("database_config must be a DatabaseConfig instance.")

        if self.ssh_config is not None and not isinstance(self.ssh_config, SSHConfig):
            raise TypeError("ssh_config must be an SSHConfig instance or None.")

        if not self.database_config.database_name:
            raise ValueError("database_name must be provided.")

        if not self.database_config.db_host:
            raise ValueError("db_host must be provided.")

        if not isinstance(self.database_config.db_port, int):
            raise TypeError("db_port must be an integer.")

        if not self.database_config.db_user:
            raise ValueError("db_user must be provided.")

        if self.database_config.db_password is None:
            self.database_config.db_password = ""
            self._verbose(
                "No database password provided. "
                "This is allowed for passwordless local connections."
            )
        elif self.database_config.db_password == "":
            self._verbose(
                "Empty database password provided. "
                "This is allowed for passwordless local connections."
            )

        supported_dialects = {"mysql"}
        if self.database_config.dialect not in supported_dialects:
            raise ValueError(
                f"Unsupported database dialect: {self.database_config.dialect}. "
                f"Supported dialects: {supported_dialects}."
            )

        supported_drivers = {"pymysql", "mysqlconnector"}
        if self.database_config.driver not in supported_drivers:
            raise ValueError(
                f"Unsupported database driver: {self.database_config.driver}. "
                f"Supported drivers: {supported_drivers}."
            )

        if self.ssh_config is None:
            return
        else:
            if not self.ssh_config.ssh_host:
                raise ValueError("ssh_host must be provided when ssh_config is used.")

            if not self.ssh_config.ssh_user:
                raise ValueError("ssh_user must be provided when ssh_config is used.")

            if not isinstance(self.ssh_config.ssh_port, int):
                raise TypeError("ssh_port must be an integer.")

            supported_ssh_auth_methods = {"ssh_key_pairs", "password"}
            if self.ssh_config.ssh_auth_method not in supported_ssh_auth_methods:
                raise ValueError(
                    f"Unsupported SSH auth method: {self.ssh_config.ssh_auth_method}. "
                    f"Supported methods: {supported_ssh_auth_methods}."
                )

            if self.ssh_config.ssh_auth_method == "password":
                if not self.ssh_config.ssh_password:
                    raise ValueError(
                        "ssh_password must be provided when ssh_auth_method='password'."
                    )

            if self.ssh_config.ssh_auth_method == "ssh_key_pairs":
                if not self.ssh_config.ssh_key_path:
                    raise ValueError("ssh_key_path must be provided when ssh_auth_method='ssh_key_pairs'.")

                if self.ssh_config.ssh_key_path == "~/.ssh/id_rsa":
                    self._verbose(
                        "Using default ssh key: ~/.ssh/id_rsa. "
                        "Set ssh_key_path if you want to use another key."
                    )

            if not self.ssh_config.local_bind_host:
                raise ValueError("local_bind_host must be provided.")

            if not isinstance(self.ssh_config.local_bind_port, int):
                raise TypeError("local_bind_port must be an integer.")

if __name__ == "__main__":
    from sqlalchemy import text

    database_config = DatabaseConfig(
        database_name="quant_datahub",
        db_host="127.0.0.1",
        db_port=3306,
        db_user="root",
        db_password="",
        dialect="mysql",
        driver="pymysql",
    )

    with SQLDatabaseConnector(
        database_config=database_config,
        ssh_config=None,
        is_verbose=True,
    ) as db:
        result = db._conn.execute(text("SELECT 1;")).fetchone()
        print(result)
