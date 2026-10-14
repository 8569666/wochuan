from app.core.config import Settings


def test_db_aliases_and_special_password():
    password = " space#'@:/?密码 "
    config = Settings(_env_file=None, DB_HOST="127.0.0.1", DB_PORT=3306,
                      DB_DATABASE="sample", DB_USERNAME="worker", DB_PASSWORD=password)
    assert config.database_url.password == password
    assert config.database_url.drivername == "mysql+aiomysql"
    assert config.database_url.database == "sample"


def test_mysql_aliases_are_supported():
    config = Settings(_env_file=None, MYSQL_HOST="localhost", MYSQL_DATABASE="sample",
                      MYSQL_USER="worker", MYSQL_PASSWORD="secret")
    assert config.database_url.username == "worker"
