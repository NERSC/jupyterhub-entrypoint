
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
async def test_uuid(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    statement = (
        select(
            dbi.model.entrypoints.c.user,
            dbi.model.entrypoints.c.uuid,
            dbi.model.entrypoints.c.entrypoint_name,
            dbi.model.entrypoints.c.entrypoint_data
        )
    )

    async with engine.begin() as conn:
        results = await conn.execute(statement)
    user, uuid, entrypoint_name, entrypoint_data = results.first()
    new_entrypoint_name = entrypoint_name + "blah"
    entrypoint_data["entrypoint_name"] = new_entrypoint_name

    async with engine.begin() as conn:
        await dbi.update_entrypoint_uuid(
            conn, user, uuid, new_entrypoint_name, entrypoint_data
        )

    statement = (
        select(
            dbi.model.entrypoints.c.user,
            dbi.model.entrypoints.c.uuid,
            dbi.model.entrypoints.c.entrypoint_name,
            dbi.model.entrypoints.c.entrypoint_data
        )
        .where(
            dbi.model.entrypoints.c.uuid==uuid
        )
    )
    async with engine.begin() as conn:
        results = await conn.execute(statement)
    user, uuid, entrypoint_name, entrypoint_data = results.first()
    assert entrypoint_name == new_entrypoint_name
    assert entrypoint_data["entrypoint_name"] == new_entrypoint_name

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

@pytest.mark.asyncio
async def test_uuid_fails(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Updating a non-existent entrypoint should fail

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.update_entrypoint_uuid(
                conn, "b", "g" * 36, "wawa", {}
            )
