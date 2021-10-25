
from sqlalchemy.sql import select, update

from jupyterhub_entrypoint.dbi.model import (
    entrypoints, entrypoint_contexts, contexts
)

# To the developer/curious:
#
# The way to think about managing selections is to consider that for each user,
# we have an association table of entrypoints and contexts (tags). This table
# tells us what entrypoints are available to be selected as default for a
# context. It could be that none of them are selected, but a user can only
# select one entrypoint for a given context. We do this by having an additional
# default-null "user" field on the entrypoint+context association table, and
# place a uniqueness constraint on (context_name, user) so that a user can only
# have one selection at most per context.
#
# All selection operations just operate on this "table," which always exists
# even if it is empty, which is why there is no create operation and the delete
# function really just does an update.

async def update_selection(conn, user, entrypoint_name, context_name):
    """Update user selection for the given context name.

    Among all user entrypoints with a given context, one may be "selected" to be
    used as the default entrypoint for that context. Selections are managed with
    the entrypoint+context association table. The act of making a selection sets
    the "user" field of the association table. A relational constraint makes
    certain that a user may only select a single entrypoint for a given context.
    Any pre-existing selection for the context is deleted first.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): Name of user entrypoint to select
        context_name    (str): Context where a selection is being made

    Raises:
        ValueError: If no entrypoint named `entrypoint_name` is found.
        ValueError: If no context named `context_name` is found.

    """

    # SQLite doesn't support multi-table update, so we take the long way.

    await delete_selection(conn, user, context_name)

    statement = select(contexts).where(contexts.c.context_name == context_name)
    results = await conn.execute(statement)
    context = results.fetchone()

    # If context doesn't exist, delete will have failed => don't need to verify

    statement = (
        select(entrypoints)
        .where(
            entrypoints.c.user == user,
            entrypoints.c.entrypoint_name == entrypoint_name
        )
    )
    results = await conn.execute(statement)
    entrypoint = results.fetchone()
    if not entrypoint:
        raise ValueError

    statement = (
        update(entrypoint_contexts)
        .values(user=user)
        .where(
            entrypoint_contexts.c.context_id == context.id,
            entrypoint_contexts.c.entrypoint_id == entrypoint.id
        )
    )
    results = await conn.execute(statement)

    # FIXME This should probably return something

async def retrieve_selection(conn, user, context_name):
    """Retrieve the selected user entrypoint's data for the given context name.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        context_name    (str): Context used to find selection

    Returns:
        dict: User entrypoint data

    Raises:
        ValueError: If no selection is found.

    """

    statement = (
        select(
            entrypoints.c.entrypoint_data,
        )
        .select_from(entrypoints)
        .join(entrypoint_contexts, isouter=True)
        .join(contexts, isouter=True)
        .where(
            entrypoint_contexts.c.user == user,
            contexts.c.context_name == context_name
        )
    )
    results = await conn.execute(statement)
    result = results.fetchone()
    if not result:
        raise ValueError

    return result.entrypoint_data

async def delete_selection(conn, user, context_name):
    """Delete user entrypoint selection for the given context name.

    TBD

    """

    statement = select(contexts).where(contexts.c.context_name == context_name)
    results = await conn.execute(statement)
    context = results.fetchone()
    if not context:
        raise ValueError

    # Actually an update, not a delete.

    statement = (
        update(entrypoint_contexts)
        .values(user=None)
        .where(
            entrypoint_contexts.c.user == user,
            entrypoint_contexts.c.context_id == context.id
        )
    )
    results = await conn.execute(statement)

    # FIXME This should probably return something
