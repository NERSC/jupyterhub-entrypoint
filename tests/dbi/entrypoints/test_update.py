
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

    # Verify that we can update an entrypoint
    
    args = entrypoint_args[len(entrypoint_args)//2]
    args = (*args[:-2], dict(hello="world"))
    async with engine.begin() as conn:
        await dbi.update_entrypoint(conn, *args)
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, *args[:2])
    assert "entrypoint_data" in output
    assert "context_names" in output
    output_entrypoint_data = output["entrypoint_data"]
    output_contexts = output["context_names"]
    assert len(output_entrypoint_data) == 1
    assert "hello" in output_entrypoint_data
    assert output_entrypoint_data["hello"] == "world"

@pytest.mark.asyncio
async def test_fails(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Updating a non-existent entrypoint should fail
    
    args = entrypoint_args[len(entrypoint_args)//2]
    args = (args[0], "quantum", args[2], dict(hello="world"))
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.update_entrypoint(conn, *args)


