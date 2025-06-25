import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django_elasticsearch_dsl.registries import registry
from django_elasticsearch_dsl.search import Search
from .documents import ProductDocument

logger = logging.getLogger("search_consumers")

class AutocompleteConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time autocomplete suggestions.

    This consumer listens for incoming WebSocket connections and receives search queries
    from the client. Upon receiving a query, it performs an Elasticsearch search on the
    Document using a combination of match, match_phrase_prefix, and fuzzy queries
    to provide both exact and similar suggestions.

    Logging is used for connection events, received queries, and errors.

    Expected client message format:
        {
            "query": "<search string>",
            "size": <number of suggestions, optional>
            "type":"<autocomplete type, e.g., 'product'>"
        }

    Response format:
        {
            "suggestions": [<list of suggested items names>]
        }
    """

    async def connect(self):
        logger.info("WebSocket connected")
        await self.accept()

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            query = data.get('query', '')
            size = data.get('size', 10) # Default size for suggestions
            search_type = data.get('type', 'product')
            logger.debug(f"Received query: {query}, size: {size}, type: {search_type}")

            if not query:
                await self.send(text_data=json.dumps({'suggestions': []}))
                return

            if search_type == "product":
                suggestions = self.product_autocomplete(query, size)
            else:
                await self.send(text_data=json.dumps({'error': 'Unknown type'}))
                return

            logger.debug(f"Suggestions: {suggestions}")
            await self.send(text_data=json.dumps({'suggestions': suggestions}))

        except Exception as e:
            logger.error(f"Error in autocomplete consumer: {e}")
            await self.send(text_data=json.dumps({'error': str(e)}))

    def product_autocomplete(self, query, size):
        search = Search(registry.get_document(ProductDocument)).query(
            "bool",
            should=[
                {"match": {"product_name": query}},
                {"match_phrase_prefix": {"product_name": query}},
                {"fuzzy": {"product_name": {"value": query, "fuzziness": "AUTO"}}},
            ],
            minimum_should_match=1,
        )[:size]
        results = search.to_queryset()
        return [result.product_name for result in results]