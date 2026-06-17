import logging
import urllib.parse
from dataclasses import dataclass
from quant_toolkit.constants import PACKAGE_PREFIX
from time import sleep
from typing import Literal
import pandas as pd
from sqlalchemy import create_engine, exc, text
from sshtunnel import SSHTunnelForwarder
from pathlib import Path

logger = logging.getLogger(__name__)

from functools import wraps
from sqlalchemy.exc import SQLAlchemyError


def sql_safe_execution(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            self.connect()
            return func(self, *args, **kwargs)
        except SQLAlchemyError as err:
            self._verbose(f"SQL execution failed in {func.__name__}: {err}")
            raise

    return wrapper


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
    verbose_prefix = f"{PACKAGE_PREFIX} SQL Connector Info: "
    error_prefix = f"{PACKAGE_PREFIX} SQL Connector Error: "

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

    @sql_safe_execution
    def execute(
            self,
            sql_query: str,
            params: dict = None,
            commit: bool = False,
    ):
        result = self._conn.execute(text(sql_query), params or {})
        if commit:
            self._conn.commit()
        return result

    @sql_safe_execution
    def commit(self):
        self._conn.commit()
        self._verbose("Transaction committed.")

    @sql_safe_execution
    def rollback(self):
        self._conn.rollback()
        self._verbose("Transaction rolled back.")

    @sql_safe_execution
    def ping(self) -> bool:
        result = self._conn.execute(text("SELECT 1;")).fetchone()
        return result is not None and result[0] == 1

    @sql_safe_execution
    def fetch_dataframe(
            self,
            sql_query: str,
            params: dict = None,
            index_col: str = None,
    ) -> pd.DataFrame:
        return pd.read_sql(text(sql_query), self._conn, params=params, index_col=index_col)

    @sql_safe_execution
    def insert_dataframe(
            self,
            df: pd.DataFrame,
            table_name: str,
            if_exists: Literal["fail", "replace", "append", "delete_rows"] = "append",
            index: bool = False,
            chunksize: int = 1000,
    ):
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{self.error_prefix} df must be a pandas DataFrame.")

        with self._engine.begin() as conn:
            df.to_sql(
                name=table_name,
                con=conn,
                if_exists=if_exists,
                index=index,
                method="multi",
                chunksize=chunksize,
            )

    @sql_safe_execution
    def table_exists(
            self,
            table_name: str,
            schema_name: str = None,
    ) -> bool:
        if not isinstance(table_name, str):
            raise TypeError(f"{self.error_prefix} table_name must be a string.")

        if not table_name:
            raise ValueError(f"{self.error_prefix} table_name must be provided.")

        if schema_name is None:
            schema_name = self.database_config.database_name

        query = """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = :schema_name
                  AND TABLE_NAME = :table_name \
                """

        result = self._conn.execute(
            text(query), {"schema_name": schema_name, "table_name": table_name,},
        )

        return result.fetchone() is not None

    @sql_safe_execution
    def show_columns(
            self,
            table_name: str,
            schema_name: str = None,
    ) -> list[str]:
        if not isinstance(table_name, str):
            raise TypeError(f"{self.error_prefix} table_name must be a string.")

        if not table_name:
            raise ValueError(f"{self.error_prefix} table_name must be provided.")

        if schema_name is None:
            schema_name = self.database_config.database_name

        query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema_name
                  AND TABLE_NAME = :table_name
                ORDER BY ORDINAL_POSITION \
                """

        result = self._conn.execute(
            text(query), {"schema_name": schema_name, "table_name": table_name,},
        )

        return [row[0] for row in result.fetchall()]

    @sql_safe_execution
    def list_tables(
            self,
            schema_name: str = None,
    ) -> list[str]:
        if schema_name is None:
            schema_name = self.database_config.database_name

        query = """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = :schema_name
                ORDER BY TABLE_NAME \
                """

        result = self._conn.execute(
            text(query), {"schema_name": schema_name,},
        )

        return [row[0] for row in result.fetchall()]

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
            raise ValueError(
                f"{self.error_prefix} Unsupported SSH auth method: {self.ssh_config.ssh_auth_method}."
            )

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
                raise RuntimeError(f"{self.error_prefix} SSH tunnel must be started before building connection URL.")
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
            raise TypeError(f"{self.error_prefix} database_config must be a DatabaseConfig instance.")

        if self.ssh_config is not None and not isinstance(self.ssh_config, SSHConfig):
            raise TypeError(f"{self.error_prefix} ssh_config must be an SSHConfig instance or None.")

        if not self.database_config.database_name:
            raise ValueError(f"{self.error_prefix} database_name must be provided.")

        if not self.database_config.db_host:
            raise ValueError(f"{self.error_prefix} db_host must be provided.")

        if not isinstance(self.database_config.db_port, int):
            raise TypeError(f"{self.error_prefix} db_port must be an integer.")

        if not self.database_config.db_user:
            raise ValueError(f"{self.error_prefix} db_user must be provided.")

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
                f"{self.error_prefix} "
                f"Unsupported database dialect: {self.database_config.dialect}. "
                f"Supported dialects: {supported_dialects}."
            )

        supported_drivers = {"pymysql", "mysqlconnector"}
        if self.database_config.driver not in supported_drivers:
            raise ValueError(
                f"{self.error_prefix} "
                f"Unsupported database driver: {self.database_config.driver}. "
                f"Supported drivers: {supported_drivers}."
            )

        if self.ssh_config is None:
            return
        else:
            if not self.ssh_config.ssh_host:
                raise ValueError(f"{self.error_prefix} ssh_host must be provided when ssh_config is used.")

            if not self.ssh_config.ssh_user:
                raise ValueError(f"{self.error_prefix} ssh_user must be provided when ssh_config is used.")

            if not isinstance(self.ssh_config.ssh_port, int):
                raise TypeError(f"{self.error_prefix} ssh_port must be an integer.")

            supported_ssh_auth_methods = {"ssh_key_pairs", "password"}
            if self.ssh_config.ssh_auth_method not in supported_ssh_auth_methods:
                raise ValueError(
                    f"{self.error_prefix} "
                    f"Unsupported SSH auth method: {self.ssh_config.ssh_auth_method}. "
                    f"Supported methods: {supported_ssh_auth_methods}."
                )

            if self.ssh_config.ssh_auth_method == "password":
                if not self.ssh_config.ssh_password:
                    raise ValueError(
                        f"{self.error_prefix} ssh_password must be provided when ssh_auth_method='password'."
                    )

            if self.ssh_config.ssh_auth_method == "ssh_key_pairs":
                if not self.ssh_config.ssh_key_path:
                    raise ValueError(f"{self.error_prefix} ssh_key_path must be provided when ssh_auth_method='ssh_key_pairs'.")

                if self.ssh_config.ssh_key_path == "~/.ssh/id_rsa":
                    self._verbose(
                        "Using default ssh key: ~/.ssh/id_rsa. "
                        "Set ssh_key_path if you want to use another key."
                    )

            if not self.ssh_config.local_bind_host:
                raise ValueError(f"{self.error_prefix} local_bind_host must be provided.")

            if not isinstance(self.ssh_config.local_bind_port, int):
                raise TypeError(f"{self.error_prefix} local_bind_port must be an integer.")

