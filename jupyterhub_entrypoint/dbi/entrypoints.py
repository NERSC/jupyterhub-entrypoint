
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
    """Create user entrypoint with optional tags"""

    # verify this thing rolls back if tagging fails

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
    """Retrieve data and tags for a user's entrypoint by name"""

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
        tag_name=None           ### remove support for not including tag_name
    ):
    """Retrieve data and tags for all of a user's matched entrypoints"""

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
    """Update user entrypoint"""

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
    """Tag user entrypoint"""

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
    """Untag user entrypoint"""

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
    """Delete user entrypoint and associated entrypoint_tags"""

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
