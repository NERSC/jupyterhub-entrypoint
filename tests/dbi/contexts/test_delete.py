
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, context_names):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

    # Delete some contexts and verify that they disappear

    async with engine.begin() as conn:
        for context_name in context_names[1:-1]:
            await dbi.delete_context(conn, context_name)
    async with engine.begin() as conn:
        output_context_names = await dbi.retrieve_contexts(conn)
    assert len(output_context_names) == 2
    assert output_context_names[0] == context_names[0]
    assert output_context_names[1] == context_names[-1]

@pytest.mark.asyncio
async def test_fails(engine, context_names):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)

    # Deleting a context that does not exist should cause an error

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.delete_context(conn, "einstein")

