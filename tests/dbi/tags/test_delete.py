
import pytest

from jupyterhub_entrypoint import dbi

@pytest.mark.asyncio
async def test_ok(engine, tag_names):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)

    # Delete some tags and verify that they disappear

    async with engine.begin() as conn:
        for tag_name in tag_names[1:-1]:
            await dbi.delete_tag(conn, tag_name)
    async with engine.begin() as conn:
        output_tag_names = await dbi.retrieve_tags(conn)
    assert len(output_tag_names) == 2
    assert output_tag_names[0] == tag_names[0]
    assert output_tag_names[1] == tag_names[-1]

@pytest.mark.asyncio
async def test_fails(engine, tag_names):
    async with engine.begin() as conn:
        for tag_name in tag_names:
            await dbi.create_tag(conn, tag_name)

    # Deleting a tag that does not exist should cause an error

    with pytest.raises(ValueError):
        async with engine.begin() as conn:
            await dbi.delete_tag(conn, "einstein")

