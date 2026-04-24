"""
Django Channels Consumers for Real-time Workflow Streaming

Provides WebSocket-based streaming for workflow execution events.
The frontend connects via WebSocket to receive real-time node transitions,
token updates, tool calls, and completion signals.
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class WorkflowStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for workflow event streaming.

    Frontend connects to /ws/workflow/<thread_id>/ and receives
    real-time events emitted by the channel layer from _run_workflow_async().

    Usage:
        ws://host/ws/workflow/<thread_id>/
    """

    async def connect(self):
        raw = self.scope["url_route"]["kwargs"]["thread_id"]
        self.thread_id = str(raw).strip().lower()
        self.group_name = f"workflow_{self.thread_id}"

        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        except Exception:
            logger.exception(
                "Workflow WS connect failed (group_add/accept).thread_id=%s channel=%s",
                self.thread_id,
                getattr(self, "channel_name", None),
            )
            # 未 accept 即返回，由 Channels 拒绝握手；便于在终端看到 Redis/配置错误栈
            return

        logger.info(
            "Workflow WS connected thread_id=%s channel=%s group=%s",
            self.thread_id,
            getattr(self, "channel_name", None),
            self.group_name,
        )

        await self.send(
            text_data=json.dumps(
                {
                    "event_type": "connected",
                    "thread_id": self.thread_id,
                }
            )
        )

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            logger.debug("group_discard skipped (connect may have failed)", exc_info=True)
        logger.info(
            "Workflow WS disconnected thread_id=%s close_code=%s channel=%s",
            getattr(self, "thread_id", None),
            close_code,
            getattr(self, "channel_name", None),
        )

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
        try:
            await self.send(text_data=json.dumps(payload))
        except Exception:
            logger.exception(
                "Workflow WS send failed thread_id=%s event_type=%s keys=%s",
                getattr(self, "thread_id", None),
                payload.get("event_type"),
                list(payload.keys())[:30],
            )
