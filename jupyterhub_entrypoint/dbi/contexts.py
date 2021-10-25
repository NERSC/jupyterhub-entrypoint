
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import insert, select, delete

from jupyterhub_entrypoint.dbi.model import contexts

async def create_context(conn, context_name):
    """Create a context for categorizing user entrypoints.

    Some entrypoints may be only appropriate for a given system configuration,
    so it makes sense to tag those entrypoints by that configuration's name.

    An entrypoint may be tagged for multiple contexts. A context usually has
    many entrypoints associated with it across all users.

    Calling this function defines a context only if it does not already exist.
    All subsequent calls with the same context name have no effect.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        context_name    (str): Meaningful contextual label

    """

    try:
        statement = insert(contexts).values(context_name=context_name)
        await conn.execute(statement)
    except IntegrityError:
        pass

async def retrieve_contexts(conn):
    """Retrieve all contexts sorted by name.

    Args:
        conn        (AsyncConnection): SQLAlchemy asyncio connection proxy

    """

    statement = select(contexts.c.context_name)
    results = await conn.execute(statement)
    return sorted([r.context_name for r in results.fetchall()])

async def delete_context(conn, context_name):
    """Delete context and all corresponding entrypoint+context tags.

    This cascades to entrypoint+context tags but does not delete any user
    entrypoint entries since it may be possible that they have or could have
    other tags.

    Attempting to delete a context using a context name that does not actually
    exist results in an error.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        context_name    (str): Meaningful contextual label

    Raises:
        ValueError: If no context named `context_name` is found.

    """

    statement = delete(contexts).where(contexts.c.context_name == context_name)
    results = await conn.execute(statement)
    if results.rowcount == 0:
        raise ValueError
