
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

    # Find untagged entrypoint, add contexts to it, verify they are there

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output["context_names"]
  
    for context_name in context_names:
        async with engine.begin() as conn:
            await dbi.tag_entrypoint(conn, user, entrypoint_name, context_name)

    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert len(output["context_names"]) == len(context_names)
    for context_name in context_names:
        assert context_name in output["context_names"]

@pytest.mark.asyncio
async def test_idempotent(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, add contexts to it multiple times, it should be OK

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output["context_names"]
 
    for i in range(2): 
        for context_name in context_names:
            async with engine.begin() as conn:
                await dbi.tag_entrypoint(conn, user, entrypoint_name, context_name)

        async with engine.begin() as conn:
            output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
        assert len(output["context_names"]) == len(context_names)
        for context_name in context_names:
            assert context_name in output["context_names"]

@pytest.mark.asyncio
async def test_entrypoint_unknown(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Tagging an entrypoint that does not exist should fail.

    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.tag_entrypoint(conn, user, "quantim", context_names[1])

@pytest.mark.asyncio
async def test_context_unknown(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, apply unknown context to it, should fail

    args = None
    for a in entrypoint_args:
        if not a[-1]:
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert not output["context_names"]

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.tag_entrypoint(conn, user, entrypoint_name, "multivac")

