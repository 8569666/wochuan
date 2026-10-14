from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8-sig",
        extra="ignore", populate_by_name=True,
    )
    host: str = Field("127.0.0.1", validation_alias=AliasChoices("MYSQL_HOST", "DB_HOST"))
    port: int = Field(3306, ge=1, le=65535,
                      validation_alias=AliasChoices("MYSQL_PORT", "DB_PORT"))
    database: str = Field("codex_db", validation_alias=AliasChoices("MYSQL_DATABASE", "DB_DATABASE"))
    username: str = Field("root", validation_alias=AliasChoices("MYSQL_USER", "DB_USERNAME"))
    password: SecretStr = Field(SecretStr(""),
                                validation_alias=AliasChoices("MYSQL_PASSWORD", "DB_PASSWORD"))
    app_origin: str = "http://127.0.0.1:5173"
    cookie_secure: bool = False
    test_database_name: str = "codex_werp_test"

    @property
    def database_url(self) -> URL:
        return URL.create("mysql+aiomysql", username=self.username,
                          password=self.password.get_secret_value(), host=self.host,
                          port=self.port, database=self.database,
                          query={"charset": "utf8mb4"})


@lru_cache
def get_settings() -> Settings:
    return Settings()
