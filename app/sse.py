from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, AsyncGenerator


class RunEventManager:
    """Manages per-run SSE event queues for real-time progress streaming."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = defaultdict(list)

    def subscribe(self, run_id: str) -> asyncio.Queue[dict[str, Any] | None]:
        """Create and register a new event queue for the given run."""
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._queues[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        """Remove a previously registered event queue for the given run."""
        if run_id in self._queues:
            self._queues[run_id] = [q for q in self._queues[run_id] if q is not queue]

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        """Broadcast an event to all subscribers of the given run."""
        for queue in self._queues.get(run_id, []):
            await queue.put(event)

    async def close(self, run_id: str) -> None:
        """Send a termination sentinel to all subscribers and remove the run's queues."""
        for queue in self._queues.get(run_id, []):
            await queue.put(None)
        self._queues.pop(run_id, None)

    async def event_stream(self, run_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted event strings until the run completes."""
        queue = self.subscribe(run_id)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            self.unsubscribe(run_id, queue)


event_manager = RunEventManager()
