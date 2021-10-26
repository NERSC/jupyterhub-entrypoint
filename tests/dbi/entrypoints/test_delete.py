
import pytest
from sqlalchemy.sql import select

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify that we can delete an entrypoint
    
    args = entrypoint_args[len(entrypoint_args)//2]
    async with engine.begin() as conn:
        await dbi.delete_entrypoint(conn, *args[:2])
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output = await dbi.retrieve_one_entrypoint(conn, *args[:2])

@pytest.mark.asyncio
async def test_fails(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Attempt to delete an entrypoint that does not exist, should fail
   
    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output = await dbi.delete_entrypoint(conn, user, "quantum")

@pytest.mark.asyncio
async def test_cascade(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            if args[-1]:
                await dbi.create_entrypoint(conn, *args)
                break
    
    async with engine.begin() as conn:
        await dbi.delete_entrypoint(conn, *args[:2])

    async with engine.begin() as conn:
        statement = select(dbi.model.entrypoint_contexts)
        results = await conn.execute(statement)
        assert len(list(results)) == 0
