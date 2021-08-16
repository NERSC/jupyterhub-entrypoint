
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

    # Find a tagged entrypoint and try selecting it, verify it's selected

    args = None
    for a in entrypoint_args:
        if len(a[-1]) == len(tag_names):
            args = a
            break

    user, entrypoint_name = args[:2]
    async with engine.begin() as conn:
        await dbi.update_selection(conn, user, entrypoint_name, tag_names[1])

    async with engine.begin() as conn:
        output_data = await dbi.retrieve_selection(conn, user, tag_names[1])
    assert len(output_data) == len(args[-2])
    for key in args[-2]:
        assert output_data[key] == args[-2][key]

@pytest.mark.asyncio
async def test_unknown(engine, tag_names, entrypoint_args):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)
    async with engine.begin() as conn:
        for args in entrypoint_args:
            await dbi.create_entrypoint(conn, *args)

    # Attempting to retrieve an unknown selection should fail

    user = entrypoint_args[0][0]
    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            output_data = await dbi.retrieve_selection(conn, user, "multivac")

