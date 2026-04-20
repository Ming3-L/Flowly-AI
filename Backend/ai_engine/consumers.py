"""
Django Channels Consumers for Real-time Workflow Streaming

Provides WebSocket-based streaming for workflow execution events.
The frontend connects via WebSocket to receive real-time node transitions,
token updates, tool calls, and completion signals.
"""

import asyncio
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class WorkflowStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for workflow event streaming.

    Frontend connects to /ws/workflow/<thread_id>/ and receives
    real-time events emitted by the channel layer from _run_workflow_async().

    Usage:
        ws://host/ws/workflow/<thread_id>/
    """

    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.group_name = f"workflow_{self.thread_id}"

        # Join the channel group for this thread
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send a connected confirmation
        await self.send(text_data=json.dumps({
            "event_type": "connected",
            "thread_id": self.thread_id,
        }))

    async def disconnect(self, close_code):
        # Leave the channel group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages from the WebSocket client.

        This is one-way streaming (server -> client), but we handle
        client commands like heartbeat pings here.
        """
        if text_data:
            try:
                data = json.loads(text_data)
                # Respond to ping with pong
                if data.get("type") == "ping":
                    await self.send(text_data=json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass

    async def workflow_event(self, event):
        """
        Handler for 'workflow_event' messages sent via channel_layer.group_send().

        This is called by the channel layer when _run_workflow_async() emits
        an event to the group.
        """
        payload = {
            "event_type": event.get("event_type", "message"),
            **event.get("data", {}),
        }
        await self.send(text_data=json.dumps(payload))
