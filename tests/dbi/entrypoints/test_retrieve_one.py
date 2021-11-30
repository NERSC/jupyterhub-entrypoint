
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

    # Verify that we can retrieve a user entrypoint by name
   
    args = entrypoint_args[len(entrypoint_args)//2]
    user, entrypoint_name = args[0], args[1]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert len(output) == 3
    assert "entrypoint_type_name" in output
    assert "entrypoint_data" in output
    assert "context_names" in output
    output_entrypoint_type_name = output["entrypoint_type_name"]
    output_entrypoint_data = output["entrypoint_data"]
    output_context_names = output["context_names"]
    assert output_entrypoint_type_name == args[2]
    for key in args[3]:
        assert output_entrypoint_data[key] == args[3][key]
    assert len(output_context_names) == len(args[4])
    for output_context_name, expected_context_name in zip(output_context_names, args[4]):
        assert output_context_name == expected_context_name

@pytest.mark.asyncio
async def test_name_xor_uuid(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # UUIDs are created on insert, so try to grab

    statement = select(
        dbi.model.entrypoints.c.user,
        dbi.model.entrypoints.c.entrypoint_type,
        dbi.model.entrypoints.c.entrypoint_name,
        dbi.model.entrypoints.c.uuid
    )
    async with engine.begin() as conn:
        results = await conn.execute(statement)
    user, entrypoint_type_name, entrypoint_name, uuid = results.first()

    # No entrypoint or UUID should fail

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output = await dbi.retrieve_one_entrypoint(conn, user)

    # Both entrypoint name and UUID should fail

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name, uuid)
     
    # Just entrypoint name should succeed

    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
        assert len(output) == 3
        assert "entrypoint_type_name" in output
        assert "entrypoint_data" in output
        assert "context_names" in output
        assert output["entrypoint_type_name"] == entrypoint_type_name
        assert output["entrypoint_data"]["user"] == user
        assert output["entrypoint_data"]["entrypoint_name"] == entrypoint_name

    # Just UUID should succeed

    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, uuid=uuid)
        assert len(output) == 3
        assert "entrypoint_type_name" in output
        assert "entrypoint_data" in output
        assert "context_names" in output
        assert output["entrypoint_type_name"] == entrypoint_type_name
        assert output["entrypoint_data"]["user"] == user
        assert output["entrypoint_data"]["entrypoint_name"] == entrypoint_name

@pytest.mark.asyncio
async def test_uuid(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # UUIDs are created on insert, so try to grab

    statement = select(
        dbi.model.entrypoints.c.user,
        dbi.model.entrypoints.c.entrypoint_type,
        dbi.model.entrypoints.c.uuid
    )
    async with engine.begin() as conn:
        results = await conn.execute(statement)
        for result in results:
            user, entrypoint_type_name, uuid = result
            output = await dbi.retrieve_one_entrypoint(conn, user, uuid=uuid)
            assert len(output) == 3
            assert "entrypoint_type_name" in output
            assert "entrypoint_data" in output
            assert "context_names" in output
            assert output["entrypoint_type_name"] == entrypoint_type_name
            assert output["entrypoint_data"]["user"] == user

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

