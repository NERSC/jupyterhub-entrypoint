
import pytest

from jupyterhub_entrypoint import dbi

@pytest.fixture
async def engine():
    async_engine = dbi.async_engine(
        f"sqlite+aiosqlite:///:memory:",
        echo=True,
        future=True
    )
    async with async_engine.begin() as conn:
        await dbi.init_db(conn, True)
    yield async_engine
    await async_engine.dispose()

@pytest.fixture
def tag_names():
    return sorted([
        "colossus",
        "guardian",
        "M5",
        "skynet",
    ])

@pytest.fixture
def users():
    return sorted([
        "forbin",
        "kuprin",
        "daystrom",
        "dyson",
    ])

@pytest.fixture
def entrypoint_names():
    return sorted([
        "mercury",
        "venus",
        "earth",
        "mars",
    ])

@pytest.fixture
def entrypoint_types():
    return sorted([
        "conda",
        "docker",
        "script",
    ])

@pytest.fixture
def entrypoint_args(users, entrypoint_names, entrypoint_types, tag_names):
    args = list()
    count = 0
    divisor = len(tag_names)+1
    for u in users:
        for n in entrypoint_names:
            for t in entrypoint_types:
                data = dict(
                    user=u,
                    entrypoint_name=f"{n}-{t}",
                    entrypoint_type=t,
                    other="/a/b/c/d"
                )
                arg = (u, f"{n}-{t}", t, data, tag_names[:count%divisor])
                args.append(arg)
                count += 1
    return args        
