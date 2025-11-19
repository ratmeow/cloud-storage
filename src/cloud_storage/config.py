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

class Config(BaseModel):
    postgres: PostgresConfig

    @classmethod
    def from_env(cls, env_path = ".env"):
        load_dotenv(env_path, override=True)
        return cls(postgres=PostgresConfig(**environ))
