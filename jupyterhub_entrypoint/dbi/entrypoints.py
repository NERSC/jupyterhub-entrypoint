
import itertools

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import insert, select, update, delete
from sqlalchemy.sql.expression import label

from jupyterhub_entrypoint.dbi.model import entrypoints, entrypoint_tags, tags

async def create_entrypoint(
    conn,
    user,
    entrypoint_name,
    entrypoint_type,
    entrypoint_data,
    tag_names=[]
):
    """Create user entrypoint with optional tags.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        entrypoint_type (str): Type of user entrypoint
        entrypoint_data (dict): Contains type-specific metadata
        tag_names       (list of str, optional): Names of tags to associate

    Raises:
        ValueError: If insertion of the entrypoint record fails.
        ValueError: If one or more named tags do not exist.

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

    if not tag_names:
        return

    statement = select(tags).where(tags.c.tag_name.in_(tag_names))
    results = await conn.execute(statement)
    tag_ids = [r.id for r in results.fetchall()]
    if len(tag_ids) != len(tag_names):
        raise ValueError

    statement = (
        insert(entrypoint_tags)
        .values(
            [dict(entrypoint_id=entrypoint_id, tag_id=t) for t in tag_ids]
        )
    )
    await conn.execute(statement)

async def retrieve_one_entrypoint(conn, user, entrypoint_name):
    """Retrieve data and tags for a user's entrypoint by name.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name

    Returns:
        tuple: dict of entrypoint data, and list of associated tag names

    Raises:
        ValueError: If no entrypoint named `entrypoint_name` is found.

    """

    statement = (
        select(
            entrypoints.c.entrypoint_data,
            tags.c.tag_name
        )
        .select_from(entrypoints)
        .join(entrypoint_tags, isouter=True)
        .join(tags, isouter=True)
        .where(
            entrypoints.c.user == user,
            entrypoints.c.entrypoint_name == entrypoint_name
        )
    )
    results = await conn.execute(statement)

    entrypoint_data = dict()
    tag_names = list()
    for r in results.fetchall():
        entrypoint_data = r.entrypoint_data
        tag_names.append(r.tag_name)
    if len(tag_names) == 1 and tag_names[0] is None:
        tag_names = list()

    if not entrypoint_data:
        raise ValueError

    return entrypoint_data, tag_names

async def retrieve_many_entrypoints(
    conn, 
    user, 
    entrypoint_type=None,
    tag_name=None
):
    """Retrieve data, selection status, and tag for a user's entrypoints.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_type (str, optional): Limit to a particular type
        tag_name        (str, optional): Limit to a particular tag

    Returns:
        dict: Key is type, value is a list of (entrypoint, selection status, 
        tag name) tuples

    """

    statement = (
        select(
            entrypoints,
            (entrypoint_tags.c.user == user).label("selected"),
            tags.c.tag_name
        )
        .select_from(entrypoints)
        .join(entrypoint_tags, isouter=True)
        .join(tags, isouter=True)
        .where(entrypoints.c.user == user)
        .order_by(
            entrypoints.c.entrypoint_type,
            entrypoints.c.entrypoint_name
        )
    )

    if entrypoint_type:
        statement = statement.where(
            entrypoints.c.entrypoint_type == entrypoint_type
        )

    if tag_name:
        statement = statement.where(
            tags.c.tag_name == tag_name
        )

    results = await conn.execute(statement)

    return dict(
        (key, list(group)) for (key, group) in itertools.groupby(
            results.fetchall(), lambda r: r.entrypoint_type
        )
    )

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
        tag_name        (str): Tag name to associate with entrypoint

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

async def _entrypoint_tag_ids(conn, user, entrypoint_name, tag_name):
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

    statement = select(tags).where(tags.c.tag_name == tag_name)
    results = await conn.execute(statement)
    tag = results.fetchone()
    if not tag:
        raise ValueError

    return entrypoint.id, tag.id

async def tag_entrypoint(conn, user, entrypoint_name, tag_name):
    """Tag user entrypoint.

    Creates an entry in the entrypoint+tag association table. This associates
    the entrypoint with the tag, and makes it eligible for selection from among
    all entrypoints associated with tags of the same name.

    If this particular entrypoint and tag are already associated, nothing
    changes.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        tag_name        (str): Tag name to associate with entrypoint

    Raises:
        ValueError: If no entrypoint named `entrypoint_name` exists.
        ValueError: If no tag named `tag_name` exists.

    """

    entrypoint_id, tag_id = await ( 
        _entrypoint_tag_ids(conn, user, entrypoint_name, tag_name)
    )

    statement = (
        insert(entrypoint_tags)
        .values(
            entrypoint_id=entrypoint_id,
            tag_id=tag_id,
            user=None
        )
    )
    try:
        results = await conn.execute(statement)
    except IntegrityError:
        pass

async def untag_entrypoint(conn, user, entrypoint_name, tag_name):
    """Remove a tag from a user entrypoint.

    Deletes the corresponding entry from the entrypoint+tag association table.
    If the tagged entrypoint happens to be a selection, then the tag will have
    no associated selection anymore.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): User-assigned entrypoint name
        tag_name        (str): Tag name to associate with entrypoint

    Raises:
        ValueError: If the entrypoint isn't actually tagged

    """

    # FIXME verify that untagging a selected entrypoint removes selection

    entrypoint_id, tag_id = await ( 
        _entrypoint_tag_ids(conn, user, entrypoint_name, tag_name)
    )

    statement = (
        delete(entrypoint_tags)
        .where(
            entrypoint_tags.c.entrypoint_id == entrypoint_id,
            entrypoint_tags.c.tag_id == tag_id
        )
    )
    results = await conn.execute(statement)
    if results.rowcount == 0:
        raise ValueError

async def delete_entrypoint(conn, user, entrypoint_name):
    """Delete user entrypoint and any associated entrypoint+tag entries.

    If any of the associated entrypoint+tag entries is a selection, then the 
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
