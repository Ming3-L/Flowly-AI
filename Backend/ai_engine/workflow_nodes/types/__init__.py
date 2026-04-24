"""
各介质节点的 ``NodeExecutor`` 具体类。
"""

from ai_engine.workflow_nodes.types.ai_chat_node import AIChatNodeExecutor
from ai_engine.workflow_nodes.types.audio_node import AudioNodeExecutor
from ai_engine.workflow_nodes.types.image_node import ImageNodeExecutor
from ai_engine.workflow_nodes.types.text_node import TextNodeExecutor
from ai_engine.workflow_nodes.types.user_custom_template_node import UserCustomTemplateNodeExecutor
from ai_engine.workflow_nodes.types.video_node import VideoNodeExecutor

__all__ = [
    "AIChatNodeExecutor",
    "AudioNodeExecutor",
    "ImageNodeExecutor",
    "TextNodeExecutor",
    "UserCustomTemplateNodeExecutor",
    "VideoNodeExecutor",
]
