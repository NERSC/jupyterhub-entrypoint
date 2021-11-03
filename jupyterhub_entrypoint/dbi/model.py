
from sqlalchemy import (
    Column, ForeignKey, Integer, JSON, MetaData,
    String, Table, Text, UniqueConstraint
)

metadata = MetaData()

contexts = Table(
    "contexts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("context_name", Text, nullable=False, unique=True)
)

entrypoints = Table(
    "entrypoints",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("uuid", String(36), nullable=False, unique=True),
    Column("user", Text, nullable=False),
    Column("entrypoint_name", Text, nullable=False),
    Column("entrypoint_type", Text, nullable=False),
    Column("entrypoint_data", JSON),
    UniqueConstraint("user", "entrypoint_name")
)

entrypoint_contexts = Table(
    "entrypoint_contexts",
    metadata,
    Column(
        "entrypoint_id",
        None,
        ForeignKey("entrypoints.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "context_id",
        None,
        ForeignKey("contexts.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column("user", Text, nullable=True),
    UniqueConstraint("context_id", "user")
)
