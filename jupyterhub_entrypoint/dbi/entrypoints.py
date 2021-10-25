
import itertools

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import insert, select, update, delete
from sqlalchemy.sql.expression import label

from jupyterhub_entrypoint.dbi.model import (
    entrypoints, entrypoint_contexts, contexts
)

async def create_entrypoint(
    conn,
    user,
    entrypoint_name,
    entrypoint_type,
    entrypoint_data,
    context_names=[]
):
    """Create user entrypoint with optional contexts.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        entrypoint_type (str): Type of user entrypoint
        entrypoint_data (dict): Contains type-specific metadata
        context_names   (list of str, optional): Context names

    Raises:
        ValueError: If insertion of the entrypoint record fails.
        ValueError: If one or more named contexts do not exist.

    """

    # FIXME verify this rolls back if tagging below fails

    statement = (
        insert(entrypoints)
        .values(
            user=user,
            entrypoint_name=entrypoint_name,
            entrypoint_type=entrypoint_type,
            entrypoint_data=entrypoint_data
        )
    )
    try:
        results = await conn.execute(statement)
    except IntegrityError:
        raise ValueError
    entrypoint_id = results.inserted_primary_key.id

    if not context_names:
        return

    statement = (
        select(contexts)
        .where(contexts.c.context_name.in_(context_names))
    )
    results = await conn.execute(statement)
    context_ids = [r.id for r in results.fetchall()]
    if len(context_ids) != len(context_names):
        raise ValueError

    statement = (
        insert(entrypoint_contexts)
        .values([
            dict(entrypoint_id=entrypoint_id, context_id=t) for t in context_ids
        ])
    )
    await conn.execute(statement)

async def retrieve_one_entrypoint(conn, user, entrypoint_name):
    """Retrieve data and contexts for a user's entrypoint by name.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name

    Returns:
        dict: Contains entrypoint data and list of context names

    Raises:
        ValueError: If no entrypoint named `entrypoint_name` is found.

    """

    statement = (
        select(
            entrypoints.c.entrypoint_data,
            contexts.c.context_name
        )
        .select_from(entrypoints)
        .join(entrypoint_contexts, isouter=True)
        .join(contexts, isouter=True)
        .where(
            entrypoints.c.user == user,
            entrypoints.c.entrypoint_name == entrypoint_name
        )
    )
    results = await conn.execute(statement)

    entrypoint_data = dict()
    context_names = list()
    for r in results.fetchall():
        entrypoint_data = r.entrypoint_data
        context_names.append(r.context_name)
    if len(context_names) == 1 and context_names[0] is None:
        context_names = list()

    if not entrypoint_data:
        raise ValueError

    return dict(entrypoint_data=entrypoint_data, context_names=context_names)

async def retrieve_many_entrypoints(
    conn,
    user,
    entrypoint_type=None,
    context_name=None
):
    """Retrieve data, selection status, and context for a user's entrypoints.

    Returns a data structure where top-level keys are context names, next-level
    keys are entrypoint type names, and the corresponding valures are a list of
    dictionaries with keys "entrypoint_data" and "selected." The former is the
    entrypoint data stored in the database, and selected is a boolean or null
    inficating whether the entrypoing is a selection.  It looks like this:

        {
          context1: {
            type1: [{
              entrypoint_data: { ... },
              selected: null
            }, {
              entrypoint_data: { ... },
              selected: true
            }],
            type2: [ ... ],
            ...
          },
          context2: {
            type1: [ ... ],
            type3: [ ... ],
          }
        }

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_type (str, optional): Limit to a particular type
        context_name    (str, optional): Limit to a particular context

    Returns:
        dict: Actually dict of dict of list of dict

    """

    statement = (
        select(
            entrypoints,
            (entrypoint_contexts.c.user == user).label("selected"),
            contexts.c.context_name
        )
        .select_from(entrypoints)
        .join(entrypoint_contexts, isouter=True)
        .join(contexts, isouter=True)
        .where(entrypoints.c.user == user)
        .order_by(
            contexts.c.context_name,
            entrypoints.c.entrypoint_type,
            entrypoints.c.entrypoint_name
        )
    )

    if entrypoint_type:
        statement = statement.where(
            entrypoints.c.entrypoint_type == entrypoint_type
        )

    if context_name:
        statement = statement.where(
            contexts.c.context_name == context_name
        )

    results = await conn.execute(statement)

    grouper = itertools.groupby(results.fetchall(), lambda r: r.context_name)
    data = dict((context_name, list(rows)) for (context_name, rows) in grouper)

    for context_name, rows in data.items():
        grouper = itertools.groupby(rows, lambda r: r.entrypoint_type)
        data[context_name] = dict((
            entrypoint_type, [{
                "entrypoint_data": r.entrypoint_data,
                "selected": r.selected
            } for r in rows]
        ) for (entrypoint_type, rows) in grouper)

    return data

async def update_entrypoint(
    conn,
    user,
    entrypoint_name,
    entrypoint_type,
    entrypoint_data
):
    """Update the user entrypoint named `entrypoint_name`.

    This makes it possible to change the entrypoint type or entrypoint data.
    Both must be supplied even if they are not being changed.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        entrypoint_type (str): Type of user entrypoint
        entrypoint_data (dict): Type-specific metadata
        context_name    (str): Context name to associate with entrypoint

    Raises:
        ValueError: If the entrypoint to update cannot be found.

    """

    # This function isn't very useful, but it also isn't being used. If we need
    # it or especially if we decide to expose it via a handler then we probably
    # need to make it a bit more flexible.

    statement = (
        update(entrypoints)
        .where(
            entrypoints.c.user == user,
            entrypoints.c.entrypoint_name == entrypoint_name
        )
        .values(
           entrypoint_type=entrypoint_type,
           entrypoint_data=entrypoint_data
        )
    )
    results = await conn.execute(statement)
    if results.rowcount == 0:
        raise ValueError

async def _entrypoint_context_ids(conn, user, entrypoint_name, context_name):
    """Utility function for tag/untag entrypoint operations"""

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

    statement = select(contexts).where(contexts.c.context_name == context_name)
    results = await conn.execute(statement)
    context = results.fetchone()
    if not context:
        raise ValueError

    return entrypoint.id, context.id

async def tag_entrypoint(conn, user, entrypoint_name, context_name):
    """Tag user entrypoint.

    Creates an entry in the entrypoint+context association table. This
    associates the entrypoint with the context, and makes it eligible for
    selection from among all entrypoints associated with contexts of the same
    name.

    If this particular entrypoint and context are already associated, nothing
    changes.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        context_name    (str): Context name to associate with entrypoint

    Raises:
        ValueError: If no entrypoint named `entrypoint_name` exists.
        ValueError: If no context named `context_name` exists.

    """

    entrypoint_id, context_id = await (
        _entrypoint_context_ids(conn, user, entrypoint_name, context_name)
    )

    statement = (
        insert(entrypoint_contexts)
        .values(
            entrypoint_id=entrypoint_id,
            context_id=context_id,
            user=None
        )
    )
    try:
        results = await conn.execute(statement)
    except IntegrityError:
        pass

async def untag_entrypoint(conn, user, entrypoint_name, context_name):
    """Remove a tag from a user entrypoint.

    Deletes the corresponding entry from the entrypoint+context association
    table. If the tagged entrypoint happens to be a selection, then the tag will
    have no associated selection anymore.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        context_name    (str): Context name to associate with entrypoint

    Raises:
        ValueError: If the entrypoint isn't actually tagged

    """

    # FIXME verify that untagging a selected entrypoint removes selection

    entrypoint_id, context_id = await (
        _entrypoint_context_ids(conn, user, entrypoint_name, context_name)
    )

    statement = (
        delete(entrypoint_contexts)
        .where(
            entrypoint_contexts.c.entrypoint_id == entrypoint_id,
            entrypoint_contexts.c.context_id == context_id
        )
    )
    results = await conn.execute(statement)
    if results.rowcount == 0:
        raise ValueError

async def delete_entrypoint(conn, user, entrypoint_name):
    """Delete user entrypoint and any associated entrypoint+context entries.

    If any of the associated entrypoint+context entries is a selection, then the
    selection is automatically deleted as well.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name

    Raises:
        ValueError: If no entrypoint with the supplied name exists.

    """

    statement = (
        delete(entrypoints)
        .where(
            entrypoints.c.user == user,
            entrypoints.c.entrypoint_name == entrypoint_name
        )
    )
    results = await conn.execute(statement)
    if results.rowcount == 0:
        raise ValueError
