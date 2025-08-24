import asyncio
import hashlib
import typing
import ujson as json
import redis.asyncio as aioredis
from functools import wraps
from redis.exceptions import ConnectionError
from pydantic import BaseModel, field_validator


class Event(BaseModel):
    """
    Event model for validating topic and managing event payloads.
    """

    topic: str
    payload: dict

    @field_validator("topic")
    def validate_topic(cls, value):
        """
        Ensure the topic follows a dot-delimited structure.
        """
        if not value or not all(part.isidentifier() for part in value.split(".")):
            raise ValueError(
                f"Invalid topic format: {value}. Topics must be dot-delimited and each part must be a valid identifier."
            )
        return value

    @property
    def checksum(self) -> str:
        """
        Return a checksum of the payload.
        """
        return hashlib.md5(json.dumps(self.payload).encode()).hexdigest()


class Event(BaseModel):
    """
    Event model for validating topic and managing event payloads.
    """

    topic: str
    payload: dict

    @field_validator("topic")
    def validate_topic(cls, value):
        """
        Ensure the topic follows a dot-delimited structure.
        """
        if not value or not all(part.isidentifier() for part in value.split(".")):
            raise ValueError(
                f"Invalid topic format: {value}. Topics must be dot-delimited and each part must be a valid identifier."
            )
        return value

    @property
    def checksum(self) -> str:
        """
        Return a checksum of the payload.
        """
        return hashlib.md5(json.dumps(self.payload).encode()).hexdigest()


class EventHub:
    """
    EventHub
    """

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.subscriptions = {}  # Map topics to a list of handlers and their timeouts
        self.subscription_tasks = []

    async def ping(self) -> bool:
        """
        Ping the Redis server to check connectivity.
        """
        try:
            return await self.redis.ping()
        except ConnectionError:
            return False

    async def close(self):
        """
        Close the Redis connection.
        """
        await self.redis.aclose()

    async def publish(self, event: Event):
        """
        Publish an event to a Redis channel.
        """
        await self.redis.publish(event.topic, event.model_dump_json())

    async def create_subscription(self, topic: str):
        """
        Create a subscription to a topic and invoke all registered handlers.
        """
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(topic)

        async def listen():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        event = Event.model_validate_json(message["data"])
                        handlers = self.subscriptions.get(topic, [])
                        for handler, timeout_ms in handlers:
                            if timeout_ms:
                                try:
                                    await asyncio.wait_for(
                                        handler(event), timeout=timeout_ms / 1000
                                    )
                                except asyncio.TimeoutError:
                                    print(
                                        f"Handler for topic '{topic}' timed out after {timeout_ms}ms"
                                    )
                            else:
                                await handler(event)
            finally:
                await pubsub.unsubscribe(topic)
                await pubsub.aclose()

        task = asyncio.create_task(listen())
        self.subscription_tasks.append(task)

    def subscribe(self, topic: str, timeout_ms: int = None):
        """
        Decorator to subscribe a function to a topic with an optional timeout.
        """

        def decorator(func: typing.Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            # Add the function and its timeout to the list of handlers for the topic
            if topic not in self.subscriptions:
                self.subscriptions[topic] = []
            self.subscriptions[topic].append((wrapper, timeout_ms))
            return wrapper

        return decorator

    async def start(self):
        """
        Start the event hub and listen to all subscribed topics.
        """
        for topic in self.subscriptions:
            await self.create_subscription(topic)
        await asyncio.gather(*self.subscription_tasks, return_exceptions=True)

    async def shutdown(self):
        """
        Shutdown the EventHub and gracefully close connections.
        """
        for task in self.subscription_tasks:
            task.cancel()
        await asyncio.gather(*self.subscription_tasks, return_exceptions=True)
        await self.close()
