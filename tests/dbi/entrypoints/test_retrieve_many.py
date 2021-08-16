
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_all_ok(engine, tag_names, entrypoint_args, users):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
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
    assert len(outputs) == len(user_entrypoint_args)

@pytest.mark.asyncio
async def test_type_ok(
        engine,
        tag_names,
        entrypoint_args,
        users,
        entrypoint_types
):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
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
async def test_tag_ok(
        engine,
        tag_names,
        entrypoint_args,
        users
):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify we can retrieve all entrypoints with a given tag for a user

    user = users[1]
    tag_name = tag_names[1]
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, None, tag_name)
    user_entrypoint_args = (
        [args for args in entrypoint_args if args[0] == user and tag_name in args[4]]
    )
    assert len(outputs) == len(user_entrypoint_args)

@pytest.mark.asyncio
async def test_type_tag_ok(
        engine,
        tag_names,
        entrypoint_args,
        users,
        entrypoint_types
):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Verify we can retrieve all entrypoints with a given tag for a user

    user = users[1]
    tag_name = tag_names[1]
    entrypoint_type = entrypoint_types[1]
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, entrypoint_type, tag_name)
    user_entrypoint_args = (
        [args for args in entrypoint_args 
            if args[0] == user and args[2] == entrypoint_type and tag_name in args[4]]
    )
    assert len(outputs) == len(user_entrypoint_args)

@pytest.mark.asyncio
async def test_type_unknown(
        engine,
        tag_names,
        entrypoint_args,
        users,
        entrypoint_types
):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
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
async def test_tag_unknown(
        engine,
        tag_names,
        entrypoint_args,
        users
):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Unknown tag should return an empty list

    user = users[1]
    tag_name = "multivac"
    async with engine.begin() as conn:
        outputs = await dbi.retrieve_many_entrypoints(conn, user, None, tag_name)
    assert len(outputs) == 0

