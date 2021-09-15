
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

    # Find a tagged entrypoint, select it, delete selection, verify it's gone

    args = None
    for a in entrypoint_args:
        if len(a[-1]) == len(tag_names):
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        await dbi.update_selection(conn, user, entrypoint_name, tag_names[1])
    async with engine.begin() as conn:
        await dbi.delete_selection(conn, user, tag_names[1])
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output_data = await dbi.retrieve_selection(conn, user, tag_names[1])

@pytest.mark.asyncio
async def test_fails(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Deleting a selection for a nonexistent tag should fail

    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.delete_selection(conn, user, "multivac")
