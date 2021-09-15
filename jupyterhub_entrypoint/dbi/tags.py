
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import insert, select, delete

from jupyterhub_entrypoint.dbi.model import tags

async def create_tag(conn, tag_name):
    """Create a tag for categorizing user entrypoints.

    Some entrypoints may be only appropriate for a given system configuration,
    so it makes sense to label those entrypoints by that configuration's name.

    An entrypoint may be associated with multiple tags. A tag usually has many
    entrypoints associated with it across all users.

    Calling this function defines a tag only if it does not already exist. All
    subsequent calls with the same tag name have no effect.

    Args:
        conn        (AsyncConnection): SQLAlchemy asyncio connection proxy
        tag_name    (str): Meaningful category label

    """

    try:
        statement = insert(tags).values(tag_name=tag_name)
        await conn.execute(statement)
    except IntegrityError:
        pass

async def retrieve_tags(conn):
    """Retrieve all tags sorted by name.

    Args:
        conn        (AsyncConnection): SQLAlchemy asyncio connection proxy

    """

    statement = select(tags.c.tag_name)
    results = await conn.execute(statement)
    return sorted([r.tag_name for r in results.fetchall()])

async def delete_tag(conn, tag_name):
    """Delete tag and all corresponding entrypoint+tag associations.

    This cascades to entrypoint+tag associations but does not delete any user
    entrypoint entries since it may be possible that they have or could have
    other tags.

    Attempting to delete a tag using a tag name that does not actually exist
    results in an error.

    Args:
        conn        (AsyncConnection): SQLAlchemy asyncio connection proxy
        tag_name    (str): Meaningful category label

    Raises:
        ValueError: If no tag named `tag_name` is found.

    """

    statement = delete(tags).where(tags.c.tag_name == tag_name)
    results = await conn.execute(statement)
    if results.rowcount == 0:
        raise ValueError
