
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, context_names):

    # Try creating some contexts

    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

@pytest.mark.asyncio
async def test_idempotent(engine, context_names):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

    # Adding a context that already exists should not change anything and
    # should not cause an error

    async with engine.begin() as conn:
        await dbi.create_context(conn, context_names[1])
    async with engine.begin() as conn:
        output_context_names = await dbi.retrieve_contexts(conn)
    for output, expected in zip(output_context_names, context_names):
        assert output == expected
