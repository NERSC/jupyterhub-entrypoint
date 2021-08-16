
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find tagged entrypoint, remove tags from it, verify they are gone

    args = None
    for a in entrypoint_args:
        if len(a[-1]) == len(tag_names):
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert len(output[1]) == len(tag_names)
  
    for tag_name in tag_names:
        async with engine.begin() as conn:
            await dbi.untag_entrypoint(conn, user, entrypoint_name, tag_name)

    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert type(output[1]) is list
    assert not output[1]

@pytest.mark.asyncio
async def test_fails(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, remove a tag from it, should fail

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output[1]

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.untag_entrypoint(conn, user, entrypoint_name, tag_name)

