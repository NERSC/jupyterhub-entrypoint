
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, tag_names):

    # Try creating some tags

    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)

@pytest.mark.asyncio
async def test_idempotent(engine, tag_names):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)

    # Adding a tag that already exists should not change anything and
    # should not cause an error

    async with engine.begin() as conn:
        await dbi.create_tag(conn, tag_names[1])
    async with engine.begin() as conn:
        output_tag_names = await dbi.retrieve_tags(conn)
    for output, expected in zip(output_tag_names, tag_names):
        assert output == expected
