import pytest
import json
import logging
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from api.asgi import application

logger = logging.getLogger("search_tests")

@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_product_autocomplete_consumer(monkeypatch):
    """
    Test the AutocompleteConsumer WebSocket consumer for product autocomplete.

    This test checks that:
    - The consumer accepts a WebSocket connection.
    - When a valid product query is sent, it returns the expected suggestions.
    - The Elasticsearch query is mocked for predictable results.
    - Logging is used for key events.
    """
    # Mock Elasticsearch results
    class DummyResult:
        def __init__(self, product_name):
            self.product_name = product_name

    def dummy_to_queryset(self):
        return [DummyResult("Test Product 1"), DummyResult("Test Product 2")]

    # Patch Search.to_queryset to return dummy results
    monkeypatch.setattr(
        "django_elasticsearch_dsl.search.Search.to_queryset",
        dummy_to_queryset
    )

    communicator = WebsocketCommunicator(application, "/ws/autocomplete/")
    connected, _ = await communicator.connect()
    logger.info(f"WebSocket connected: {connected}")
    assert connected

    await communicator.send_to(text_data=json.dumps({
        "query": "Test",
        "type": "product"
    }))
    logger.info("Sent query: Test")
    response = await communicator.receive_from()
    logger.info(f"Received response: {response}")
    data = json.loads(response)
    assert "suggestions" in data
    assert data["suggestions"] == ["Test Product 1", "Test Product 2"]

    await communicator.disconnect()
    logger.info("WebSocket disconnected")