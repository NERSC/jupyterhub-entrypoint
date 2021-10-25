
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

    # Verify that we can retrieve a user entrypoint by name
   
    args = entrypoint_args[len(entrypoint_args)//2]
    user, entrypoint_name = args[0], args[1]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert len(output) == 2
    assert "entrypoint_data" in output
    assert "context_names" in output
    output_entrypoint_data = output["entrypoint_data"]
    output_context_names = output["context_names"]
    for key in args[3]:
        assert output_entrypoint_data[key] == args[3][key]
    assert len(output_context_names) == len(args[4])
    for output_context_name, expected_context_name in zip(output_context_names, args[4]):
        assert output_context_name == expected_context_name

@pytest.mark.asyncio
async def test_fails(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Retrieving an entrypoint using a name that does not exist should fail

    args = entrypoint_args[len(entrypoint_args)//2]
    user = args[0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output = await dbi.retrieve_one_entrypoint(conn, user, "quantum-fortran")

