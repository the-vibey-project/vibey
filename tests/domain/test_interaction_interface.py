import asyncio
import pytest
from vibey.domain.interfaces.interaction_interface import InMemoryInteractionFake

@pytest.mark.asyncio
async def test_inmemory_echo():
    fake = InMemoryInteractionFake()
    response = await fake.send("hello")
    assert response == "Echo: hello"
