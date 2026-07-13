import json
import logging
import asyncio
from typing import Callable, Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.database import db_manager

logger = logging.getLogger(__name__)

class SystemEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    sender: str
    payload: Dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[SystemEvent], Any]]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None
        self._is_listening = False

    async def publish(self, topic: str, sender: str, payload: Dict[str, Any]) -> None:
        """Publishes an event to the specified Redis pub/sub channel."""
        event = SystemEvent(topic=topic, sender=sender, payload=payload)
        event_str = json.dumps(event.model_dump())

        if topic == "permission.response":
            logger.info(f"PUBLISH: permission.response event_id={event.event_id}, payload={payload}")

        try:
            redis = db_manager.redis_client
            if redis:
                if topic == "permission.response":
                    logger.info(f"PUBLISH: permission.response via REDIS")
                await redis.publish(topic, event_str)
                logger.debug(f"Event published to topic '{topic}': {event.event_id}")
            else:
                # In-memory fallback
                if topic == "permission.response":
                    logger.info(f"PUBLISH: permission.response via IN-MEMORY fallback")
                logger.debug(f"In-Memory fallback: dispatching event to '{topic}' directly.")
                await self._dispatch_event(topic, event)
        except Exception as e:
            logger.error(f"Failed to publish event to {topic}: {e}")

    def subscribe(self, topic: str, handler: Callable[[SystemEvent], Any]) -> None:
        """Registers an in-memory handler for a topic. The handler will be called when an event on the topic arrives."""
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)
        logger.info(f"Registered subscriber for topic '{topic}'")

    def unsubscribe(self, topic: str, handler: Callable[[SystemEvent], Any]) -> None:
        """Removes a previously registered handler for a topic."""
        if topic in self._handlers:
            try:
                self._handlers[topic].remove(handler)
            except ValueError:
                pass

    async def start_listening(self) -> None:
        """Starts the background Redis pub/sub listening loop."""
        if self._is_listening:
            return

        self._is_listening = True
        self._pubsub_task = asyncio.create_task(self._listen_loop())
        logger.info("Event Bus background listener started.")

    async def stop_listening(self) -> None:
        """Stops the background listener loop."""
        self._is_listening = False
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
            logger.info("Event Bus background listener stopped.")

    async def _listen_loop(self) -> None:
        """Subscribes to all registered topics in Redis and dispatches events to registered callbacks."""
        subscribed_topics: set = set()
        pubsub = None

        while self._is_listening:
            try:
                redis = db_manager.redis_client
                if not redis:
                    await asyncio.sleep(1)
                    continue

                current_topics = set(self._handlers.keys())

                if current_topics != subscribed_topics:
                    if pubsub:
                        try:
                            await pubsub.unsubscribe()
                            await pubsub.close()
                        except Exception:
                            pass

                    pubsub = redis.pubsub()
                    topics_to_sub = list(current_topics)
                    await pubsub.subscribe(*topics_to_sub)

                    if not subscribed_topics:
                        logger.info(f"Redis PubSub initial subscribe: {topics_to_sub}")
                    else:
                        logger.info(f"Redis PubSub re-subscribe (was {list(subscribed_topics)}, now {topics_to_sub})")

                    subscribed_topics = current_topics.copy()

                if not subscribed_topics:
                    await asyncio.sleep(0.5)
                    continue

                while self._is_listening:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                    if message:
                        channel = message["channel"]
                        data_str = message["data"]
                        try:
                            data = json.loads(data_str)
                            event = SystemEvent(**data)
                            await self._dispatch_event(channel, event)
                        except Exception as e:
                            logger.error(f"Error parsing event on channel {channel}: {e}")

                    if set(self._handlers.keys()) != subscribed_topics:
                        logger.info("Topic list changed, re-subscribing")
                        break

                    await asyncio.sleep(0.005)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Exception in Event Bus listen loop: {e}")
                await asyncio.sleep(2)

    async def _dispatch_event(self, topic: str, event: SystemEvent) -> None:
        """Invokes all registered callbacks for the given topic concurrently."""
        handlers = self._handlers.get(topic, [])
        if not handlers:
            logger.debug(f"No handlers for topic '{topic}', skipping dispatch")
            if topic == "permission.response":
                logger.warning(f"DISPATCH: permission.response has NO handlers! Registered topics: {list(self._handlers.keys())}")
            return

        if topic == "permission.response":
            logger.info(f"DISPATCH: permission.response event {event.event_id} -> {len(handlers)} handler(s)")

        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(event)))
            else:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in synchronous event handler for topic {topic}: {e}")
        
        if tasks:
            logger.debug(f"Dispatching event {event.event_id} on topic '{topic}' to {len(tasks)} async handlers")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    logger.error(f"Error in async event handler #{i} for topic {topic}: {res}")

event_bus = EventBus()
