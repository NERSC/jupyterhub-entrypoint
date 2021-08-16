
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, add tags to it, verify they are there

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output[1]
  
    for tag_name in tag_names:
        async with engine.begin() as conn:
            await dbi.tag_entrypoint(conn, user, entrypoint_name, tag_name)

    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert len(output[1]) == len(tag_names)
    for tag_name in tag_names:
        assert tag_name in output[1]

@pytest.mark.asyncio
async def test_idempotent(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, add tags to it multiple times, it should be OK

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output[1]
 
    for i in range(2): 
        for tag_name in tag_names:
            async with engine.begin() as conn:
                await dbi.tag_entrypoint(conn, user, entrypoint_name, tag_name)

        async with engine.begin() as conn:
            output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
        assert len(output[1]) == len(tag_names)
        for tag_name in tag_names:
            assert tag_name in output[1]

@pytest.mark.asyncio
async def test_entrypoint_unknown(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Tagging an entrypoint that does not exist should fail.

    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.tag_entrypoint(conn, user, "quantim", tag_names[1])

@pytest.mark.asyncio
async def test_tag_unknown(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, apply unknown tag to it, should fail

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output[1]

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.tag_entrypoint(conn, user, entrypoint_name, "multivac")

