
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

    # Find tagged entrypoint, remove contexts from it, verify they are gone

    args = None
    for a in entrypoint_args:
        if len(a[-1]) == len(context_names):
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert len(output["context_names"]) == len(context_names)
  
    for context_name in context_names:
        async with engine.begin() as conn:
            await dbi.untag_entrypoint(conn, user, entrypoint_name, context_name)

    async with engine.begin() as conn:
        output = await dbi.retrieve_one_entrypoint(conn, user, entrypoint_name)
    assert type(output["context_names"]) is list
    assert not output["context_names"]

@pytest.mark.asyncio
async def test_fails(engine, context_names, entrypoint_args):
    async with engine.begin() as conn:
        for context_name in context_names:
            await dbi.create_context(conn, context_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Find untagged entrypoint, remove a context from it, should fail

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
            await dbi.untag_entrypoint(conn, user, entrypoint_name, context_name)

