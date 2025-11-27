from sqlalchemy import UUID, Column, String, Table
from sqlalchemy.orm import registry

from cloud_storage.domain.models import User

mapper_registry = registry()
users_table = Table(
    "users",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("login", String),
    Column("hashed_password", String),
)

mapper_registry.map_imperatively(User, users_table)
