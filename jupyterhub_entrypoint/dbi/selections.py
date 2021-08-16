
from sqlalchemy.sql import select, update

from jupyterhub_entrypoint.dbi.model import entrypoints, entrypoint_tags, tags

async def update_selection(conn, user, entrypoint_name, tag_name):
    """Update user selection for the given tag name"""

    # SQLite doesn't support multi-table update

    await delete_selection(conn, user, tag_name)

    statement = select(tags).where(tags.c.tag_name == tag_name)
    results = await conn.execute(statement)
    tag = results.fetchone()

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
        update(entrypoint_tags)
        .values(user=user)
        .where(
            entrypoint_tags.c.tag_id == tag.id,
            entrypoint_tags.c.entrypoint_id == entrypoint.id
        )
    )
    results = await conn.execute(statement)

async def retrieve_selection(conn, user, tag_name):
    """Retrieve data for a user's selection by tag name"""

    statement = (
        select(
            entrypoints.c.entrypoint_data,
        )
        .select_from(entrypoints)
        .join(entrypoint_tags, isouter=True)
        .join(tags, isouter=True)
        .where(
            entrypoint_tags.c.user == user,
            tags.c.tag_name == tag_name
        )
    )

    results = await conn.execute(statement)
    result = results.fetchone()
    if not result:
        raise ValueError

    return result.entrypoint_data

async def delete_selection(conn, user, tag_name):
    """Delete user selection for the given tag name"""

    statement = select(tags).where(tags.c.tag_name == tag_name)
    results = await conn.execute(statement)
    tag = results.fetchone()
    if not tag:
        raise ValueError

    statement = (
        update(entrypoint_tags)
        .values(user=None)
        .where(
            entrypoint_tags.c.user == user,
            entrypoint_tags.c.tag_id == tag.id
        )
    )
    results = await conn.execute(statement)
