
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find a tagged entrypoint and try selecting it

    args = None
    for a in entrypoint_args:
        if len(a[-1]) == len(context_names):
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        await dbi.update_selection(conn, user, entrypoint_name, context_names[1])

@pytest.mark.asyncio
async def test_context_unknown(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Try selecting an entrypoint tagged with an unknown context, should fail

    user, entrypoint_name = entrypoint_args[0][:2]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.update_selection(conn, user, entrypoint_name, "multivac")

@pytest.mark.asyncio
async def test_entrypoint_unknown(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Try selecting an unknown entrypoint,

    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.update_selection(conn, user, "quantum", context_names[1])

