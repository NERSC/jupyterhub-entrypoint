
from sqlalchemy.sql import select, update

from jupyterhub_entrypoint.dbi.model import entrypoints, entrypoint_tags, tags

# To the developer/curious:
#
# The way to think about managing selections is to consider that for each user,
# we have an association table of entrypoints and tags. This table tells us
# what entrypoints are available to be selected as default for a tag. It could
# be that none of them are selected, but a user can only select one entrypoint
# for a given tag. We do this by having an additional default-null "user" field
# on the entrypoint+tag association table, and place a uniqueness constraint on
# (tag_name, user) so that a user can only have one selection at most per tag.
#
# All selection operations just operate on this "table," which always exists
# even if it is empty, which is why there is no create operation and the delete
# function really just does an update.

async def update_selection(conn, user, entrypoint_name, tag_name):
    """Update user selection for the given tag name.

    Among all user entrypoints with a given tag, one may be "selected" to be
    used as the default entrypoint for that tag. Selections are managed with
    the entrypoint+tag association table. The act of making a selection sets
    the "user" field of the association table. A relational constraint makes
    certain that a user may only select a single entrypoint for a given tag.
    Any pre-existing selection for the tag is deleted first.

    Args:
        conn            (AsyncConnection): SQLAlchemy asyncio connection proxy
        user            (str): User name
        entrypoint_name (str): Name of user entrypoint to select
        tag_name        (str): Tag where a selection is being made

    Raises:
        ValueError: If no entrypoint named `entrypoint_name` is found.
        ValueError: If no tag named `tag_name` is found.

    """

    # SQLite doesn't support multi-table update, so we take the long way.

    await delete_selection(conn, user, tag_name)

    statement = select(tags).where(tags.c.tag_name == tag_name)
    results = await conn.execute(statement)
    tag = results.fetchone()
    
    # If tag doesn't exist, delete will have failed => don't need to verify it.

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

    # FIXME This should probably return something

async def retrieve_selection(conn, user, tag_name):
    """Retrieve the selected user entrypoint's data for the given tag name.

    Args:
        conn:       (AsyncConnection): SQLAlchemy asyncio connection proxy
        user        (str): User name
        tag_name    (str): Tag used to find selection

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
    """Delete user entrypoint selection for the given tag name.

     

    """

    statement = select(tags).where(tags.c.tag_name == tag_name)
    results = await conn.execute(statement)
    tag = results.fetchone()
    if not tag:
        raise ValueError

    # Actually an update, not a delete.

    statement = (
        update(entrypoint_tags)
        .values(user=None)
        .where(
            entrypoint_tags.c.user == user,
            entrypoint_tags.c.tag_id == tag.id
        )
    )
    results = await conn.execute(statement)

    # FIXME This should probably return something

