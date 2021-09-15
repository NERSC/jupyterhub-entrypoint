
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

    # Find a tagged entrypoint and try selecting it

    args = None
    for a in entrypoint_args:
        if len(a[-1]) == len(tag_names):
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        await dbi.update_selection(conn, user, entrypoint_name, tag_names[1])

@pytest.mark.asyncio
async def test_tag_unknown(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Try selecting an entrypoint with an unknown tag, should fail

    user, entrypoint_name = entrypoint_args[0][:2]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.update_selection(conn, user, entrypoint_name, "multivac")

@pytest.mark.asyncio
async def test_entrypoint_unknown(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Try selecting an unknown entrypoint,

    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.update_selection(conn, user, "quantum", tag_names[1])

