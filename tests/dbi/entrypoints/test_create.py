
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

    # Try creating some entrypoints

    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

@pytest.mark.asyncio
async def test_contexts_ok(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

    # Creating an entrypoint with an unknown context name should fail
    
    args = (*entrypoint_args[1][:-1], entrypoint_args[1][-1] + ["multivac"])
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.create_entrypoint(conn, *args)

@pytest.mark.asyncio
async def test_name_ok(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Creating an entrypoint with a name used by the user already should fail
   
    args = entrypoint_args[-1]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.create_entrypoint(conn, *args)

