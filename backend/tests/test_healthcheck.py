import pytest


@pytest.mark.asyncio
async def test_smoke():
    assert 2 + 2 == 4
