"""
Realtime Emotion Module

This module provides real-time emotion detection and processing capabilities.
"""

__version__ = "1.0.0"
__author__ = "Lenovo Emotion Team"

from .realtime_emotion_interface import create_realtime_emotion_interface

__all__ = ["create_realtime_emotion_interface"]
