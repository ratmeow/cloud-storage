from pydantic import BaseModel, Field
from dotenv import load_dotenv
from os import environ

class PostgresConfig(BaseModel):
    user: str = Field(validation_alias="POSTGRES_USER")
    password: str = Field(validation_alias="POSTGRES_PASSWORD")
    db: str = Field(validation_alias="POSTGRES_DB")
    host: str = Field(validation_alias="POSTGRES_HOST")
    port: str = Field(validation_alias="POSTGRES_PORT")

    @property
    def pg_async_url(self):
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

class RedisConfig(BaseModel):
    host: str = Field(validation_alias="REDIS_HOST")
    port: int = Field(validation_alias="REDIS_PORT")
    session_lifetime: int = Field(validation_alias="REDIS_SESSION_LIFETIME_SEC")


class Config(BaseModel):
    postgres: PostgresConfig
    redis: RedisConfig

    @classmethod
    def from_env(cls, env_path = ".env"):
        load_dotenv(env_path, override=True)
        return cls(postgres=PostgresConfig(**environ), redis=RedisConfig(**environ))
