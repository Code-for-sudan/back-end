import json
import re
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from asyncio import create_task, sleep, CancelledError
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

    Connections

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
    If no suggestions are found:
        {
            "suggestions": [],
            "message": "No similar products were found."
        }
    If an error occurs:
        {
            "error": "<error message>"
        }
    """

    MAX_SIZE = 15
    DEFAULT_SIZE = 10
    TIMEOUT_SECONDS = 60  # Timeout for inactivity

    async def connect(self):
        logger.info("WebSocket connected")
        await self.accept()
        self.inactivity_task = create_task(self.start_inactivity_timer())

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: {close_code}")
        if hasattr(self, 'inactivity_task'):
            self.inactivity_task.cancel()

    async def receive(self, text_data):
        # Reset inactivity timer on every message
        if hasattr(self, 'inactivity_task'):
            self.inactivity_task.cancel()
        self.inactivity_task = create_task(self.start_inactivity_timer())

        try:
            data = json.loads(text_data)
            query = data.get('query', '')
            query = re.sub(r'[^\w\s\-]', '', query).strip() # Sanitize input

            # Validate and set size
            raw_size = data.get('size', self.DEFAULT_SIZE)
            try:
                size = int(raw_size)
                if size < 1 or size > self.MAX_SIZE:
                    size = self.DEFAULT_SIZE
            except (TypeError, ValueError):
                size = self.DEFAULT_SIZE
            search_type = data.get('type', 'product')
            logger.debug(f"Received query: {query}, size: {size}, type: {search_type}")

            if not query:
                await self.send(text_data=json.dumps({'suggestions': [], 'message': 'Empty query'}))
                return

            # Add search types here as needed
            if search_type == "product":
                response = await self.product_autocomplete(query, size)
                await self.send(text_data=json.dumps(response))
                logger.debug(f"Sent response: {response}")
            else:
                await self.send(text_data=json.dumps({'error': 'Unknown type'}))
                return

        except Exception as e:
            logger.error(f"Error in autocomplete consumer: {e}")
            await self.send(text_data=json.dumps({'error': str(e)}))

    async def product_autocomplete(self, query, size):
        search = ProductDocument.search().query(
            "bool",
            should=[
                {"match": {"product_name": query}},
                {"match_phrase_prefix": {"product_name": query}},
                {"fuzzy": {"product_name": {"value": query, "fuzziness": "AUTO"}}},
            ],
            minimum_should_match=1,
        )[:size]

        results = await sync_to_async(search.execute)()
        suggestions = [hit.product_name for hit in results]

        if not suggestions:
            return {
                'suggestions': [],
                'message': 'No similar products were found.'
            }

        return {
            'suggestions': suggestions
        }
    
    async def start_inactivity_timer(self):
        try:
            await sleep(self.TIMEOUT_SECONDS)
            logger.info("WebSocket closed due to inactivity.")
            await self.close()
        except CancelledError:
            # Timer was cancelled due to new activity
            pass