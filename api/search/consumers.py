import json
import re
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from asyncio import create_task, sleep, CancelledError
from accounts.models import BusinessOwner
from .documents import ProductDocument

logger = logging.getLogger("search_consumers")

class AutocompleteConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time autocomplete suggestions.
    This consumer listens for incoming WebSocket connections and receives search queries
    from the client. Upon receiving a query, it performs an Elasticsearch search on the
    Document using a combination of match, match_phrase_prefix, and fuzzy queries
    to provide both exact and similar suggestions.

    It supports role-based filtering
    
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
    TIMEOUT_SECONDS = 60

    async def connect(self):
        # Assign authenticated user from JWT middleware
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            logger.warning("Unauthorized WebSocket attempt.")
            await self.close()
            return

        await self.accept()
        self.inactivity_task = create_task(self.start_inactivity_timer())
        logger.info(f"Connected: user {self.user.id}")

    async def disconnect(self, close_code):
        logger.info(f"Disconnected: {close_code}")
        if hasattr(self, 'inactivity_task'):
            self.inactivity_task.cancel()

    async def receive(self, text_data):
        # Reset inactivity timer
        if hasattr(self, 'inactivity_task'):
            self.inactivity_task.cancel()
        self.inactivity_task = create_task(self.start_inactivity_timer())

        try:
            data = json.loads(text_data)
            query = re.sub(r'[^\w\s\-]', '', data.get('query', '')).strip()
            raw_size = data.get('size', self.DEFAULT_SIZE)

            # Validate size limit
            try:
                size = int(raw_size)
                if size < 1 or size > self.MAX_SIZE:
                    size = self.DEFAULT_SIZE
            except (TypeError, ValueError):
                size = self.DEFAULT_SIZE

            # Handle autocomplete type
            search_type = data.get('type', 'product')

            if not query:
                await self.send(text_data=json.dumps({'suggestions': [], 'message': 'Empty query'}))
                return

            # Search based on type, add types here as needed
            if search_type == "product":
                # If business owner → search own products, else → global search
                if await self.is_business_owner(self.user):
                    store_id = await self.get_user_store_id(self.user)
                    response = await self.business_owner_autocomplete(query, size, store_id)
                else:
                    response = await self.product_autocomplete(query, size)

                await self.send(text_data=json.dumps(response))
            else:
                await self.send(text_data=json.dumps({'error': 'Unknown search type'}))

        except Exception as e:
            logger.error(f"Error: {e}")
            await self.send(text_data=json.dumps({'error': str(e)}))

    async def product_autocomplete(self, query, size):
        # Search across all products
        search = ProductDocument.search().query(
            "bool",
            should=[
                {"match": {"product_name": query}},
                {"match_phrase_prefix": {"product_name": query}},
                {"fuzzy": {"product_name": {"value": query, "fuzziness": "AUTO"}}},
            ],
            minimum_should_match=1
        )[:size]

        results = await sync_to_async(search.execute)()
        suggestions = [hit.product_name for hit in results]
        return {'suggestions': suggestions} if suggestions else {
            'suggestions': [], 'message': 'No similar products found.'}

    async def business_owner_autocomplete(self, query, size, store_id):
        # Filter products to the owner's store only
        search = ProductDocument.search().query(
            "bool",
            must=[{"term": {"store_id": store_id}}],
            should=[
                {"match": {"product_name": query}},
                {"match_phrase_prefix": {"product_name": query}},
                {"fuzzy": {"product_name": {"value": query, "fuzziness": "AUTO"}}},
            ],
            minimum_should_match=1
        )[:size]

        results = await sync_to_async(search.execute)()
        suggestions = [hit.product_name for hit in results]
        return {'suggestions': suggestions} if suggestions else {
            'suggestions': [], 'message': 'No similar products found in your store.'}

    async def start_inactivity_timer(self):
        try:
            await sleep(self.TIMEOUT_SECONDS)
            logger.info("Inactivity timeout")
            await self.close()
        except CancelledError:
            pass

    @sync_to_async
    def is_business_owner(self, user):
        return BusinessOwner.objects.filter(user=user).exists()

    @sync_to_async
    def get_user_store_id(self, user):
        try:
            return BusinessOwner.objects.get(user=user).store.id
        except BusinessOwner.DoesNotExist:
            return None
