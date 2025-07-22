# 📦 src/models/__init__.py
"""
Data Models - Smart Detection
"""
from .detection_model import (
    DetectionState,
    SystemStatus, 
    DetectionValues,
    TrainingCounters,
    PLCStatus,
    ComponentStatus,
    SystemData,
    WebSocketCommand,
    TrainingImage,
    TrainingStats
)

__all__ = [
    'DetectionState',
    'SystemStatus',
    'DetectionValues', 
    'TrainingCounters',
    'PLCStatus',
    'ComponentStatus',
    'SystemData',
    'WebSocketCommand',
    'TrainingImage',
    'TrainingStats'
]
