
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, tag_names):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)

    # Retrieve created tags and verify them

    async with engine.begin() as conn:
        output_tag_names = await dbi.retrieve_tags(conn)
    for output, expected in zip(output_tag_names, tag_names):
        assert output == expected

