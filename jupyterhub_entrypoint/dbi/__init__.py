
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine

from .model import metadata

from .entrypoints import (
    create_entrypoint,
    retrieve_one_entrypoint,
    retrieve_many_entrypoints,
    update_entrypoint,
    tag_entrypoint,
    untag_entrypoint,
    delete_entrypoint
)

from .selections import (
    update_selection,
    retrieve_selection,
    delete_selection
)

from .contexts import (
    create_context,
    retrieve_contexts,
    delete_context
)

def async_engine(*args, **kwargs):
    engine = create_async_engine(*args, **kwargs)
    if engine.name == "sqlite":
        register_foreign_keys()
    return engine

def register_foreign_keys(): # pragma: no cover
    """Enable deletes with cascade in e.g. sqlite"""
    @event.listens_for(Engine, "connect")
    def connect(dbi_connection, connection_record):
        cursor = dbi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async def init_db(conn, drop_all=False):
    if drop_all:
        await conn.run_sync(metadata.drop_all)
    await conn.run_sync(metadata.create_all)
