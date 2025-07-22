# 📦 src/services/__init__.py
"""
External Services - Smart Detection
"""
from .camera_service import camera_service
from .plc_service import plc_service  
from .websocket_service import websocket_service
from .ai_service import ai_service

__all__ = [
    'camera_service',
    'plc_service', 
    'websocket_service',
    'ai_service'
]
