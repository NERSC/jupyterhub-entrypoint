
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, context_names):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

    # Retrieve created contexts and verify them

    async with engine.begin() as conn:
        output_context_names = await dbi.retrieve_contexts(conn)
    for output, expected in zip(output_context_names, context_names):
        assert output == expected

