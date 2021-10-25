
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_all_ok(engine, context_names, entrypoint_args, users):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify we can retrieve all entrypoints for a user, could be more exhaustive

    user = users[1]
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user)
    user_entrypoint_args = (
        [args for args in entrypoint_args if args[0] == user]
    )

    for (user, entrypoint_name, entrypoint_type, data, context_names) in user_entrypoint_args:
        for context_name in context_names:
            assert next((
                True for x in outputs[context_name][entrypoint_type] if 
                x["entrypoint_data"]["user"] == user and 
                x["entrypoint_data"]["entrypoint_name"] == entrypoint_name and
                x["entrypoint_data"]["entrypoint_type"] == entrypoint_type and
                all([x["entrypoint_data"][key] == data[key] for key in data])
            ), False)

@pytest.mark.asyncio
async def test_type_ok(
    engine,
    context_names,
    entrypoint_args,
    users,
    entrypoint_types
):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify we can retrieve all entrypoints of a given type for a user

    user = users[1]
    entrypoint_type = entrypoint_types[1]
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, entrypoint_type)
    user_entrypoint_args = (
        [args for args in entrypoint_args if args[0] == user and args[2] == entrypoint_type]
    )
    assert len(outputs) == len(user_entrypoint_args)

@pytest.mark.asyncio
async def test_context_ok(
    engine,
    context_names,
    entrypoint_args,
    users
):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify we can retrieve all entrypoints with a given context for a user

    user = users[1]
    context_name = context_names[1]
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, None, context_name)
    user_entrypoint_args = (
        [args for args in entrypoint_args if args[0] == user and context_name in args[4]]
    )
    
    for (user, entrypoint_name, entrypoint_type, data, _) in user_entrypoint_args:
        assert next((
            True for x in outputs[context_name][entrypoint_type] if 
            x["entrypoint_data"]["user"] == user and 
            x["entrypoint_data"]["entrypoint_name"] == entrypoint_name and
            x["entrypoint_data"]["entrypoint_type"] == entrypoint_type and
            all([x["entrypoint_data"][key] == data[key] for key in data])
        ), False)

@pytest.mark.asyncio
async def test_type_context_ok(
    engine,
    context_names,
    entrypoint_args,
    users,
    entrypoint_types
):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify we can retrieve all entrypoints with a given context for a user

    user = users[1]
    context_name = context_names[1]
    entrypoint_type = entrypoint_types[1]
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, entrypoint_type, context_name)
    user_entrypoint_args = (
        [args for args in entrypoint_args 
            if args[0] == user and args[2] == entrypoint_type and context_name in args[4]]
    )

    for (user, entrypoint_name, _, data, _) in user_entrypoint_args:
        assert next((
            True for x in outputs[context_name][entrypoint_type] if 
            x["entrypoint_data"]["user"] == user and 
            x["entrypoint_data"]["entrypoint_name"] == entrypoint_name and
            x["entrypoint_data"]["entrypoint_type"] == entrypoint_type and
            all([x["entrypoint_data"][key] == data[key] for key in data])
        ), False)

@pytest.mark.asyncio
async def test_type_unknown(
    engine,
    context_names,
    entrypoint_args,
    users,
    entrypoint_types
):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Unknown type should return an empty list

    user = users[1]
    entrypoint_type = "quantum"
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, entrypoint_type)
    assert len(outputs) == 0

@pytest.mark.asyncio
async def test_context_unknown(
    engine,
    context_names,
    entrypoint_args,
    users
):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Unknown context should return an empty list

    user = users[1]
    context_name = "multivac"
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, None, context_name)
    assert len(outputs) == 0
