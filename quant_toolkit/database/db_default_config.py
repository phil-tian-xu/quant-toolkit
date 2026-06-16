import os


default_logging_info = {
    # SSH connection info
    "is_ssh": True,
    "ssh_host": "188.245.87.16",
    "ssh_port": 22,
    "ssh_user": "sif_user_2025",
    "ssh_auth_method": "password",
    "ssh_password": os.environ.get("QUANT_DB_SSH_PASSWORD", "sif_2025!"),

    # Database connection info
    "db_host": "127.0.0.1",
    "db_port": 3306,
    "db_user": "sif_db_ro_2025",
    "db_password": os.environ.get("QUANT_DB_PASSWORD", "RO2025!"),
    "database_name": "sif_test_db",
    "dialect": "mysql",
    "driver": "pymysql",
}
