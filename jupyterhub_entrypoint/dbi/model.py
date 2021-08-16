
from sqlalchemy import (
    Column, ForeignKey, Integer, JSON, MetaData, Table, Text, UniqueConstraint
)

metadata = MetaData()

tags = Table(
    "tags",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tag_name", Text, nullable=False, unique=True)
)

entrypoints = Table(
    "entrypoints",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user", Text, nullable=False),
    Column("entrypoint_name", Text, nullable=False),
    Column("entrypoint_type", Text, nullable=False),
    Column("entrypoint_data", JSON),
    UniqueConstraint("user", "entrypoint_name")
)

entrypoint_tags = Table(
    "entrypoint_tags",
    metadata,
    Column(
        "entrypoint_id", 
        None, 
        ForeignKey("entrypoints.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "tag_id",
        None,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column("user", Text, nullable=True),
    UniqueConstraint("tag_id", "user")
)
