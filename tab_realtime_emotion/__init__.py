"""
Realtime Emotion Module

This module provides real-time emotion detection and processing capabilities.
"""
import torch.nn as nn

from .AV_Base import AV_Base
from .AV_Base_v2 import AV_Base_v2
from .AV_Base_v3 import AV_Base_v3

__version__ = "1.0.0"
__author__ = "Lenovo Emotion Team"

from .realtime_emotion_interface import create_realtime_emotion_interface

__all__ = ["create_realtime_emotion_interface"]

class get_models(nn.Module):
    def __init__(self, args):
        super(get_models, self).__init__()

        MODEL_MAP = {
            "AV_Base": AV_Base,
            "AV_Base_v2": AV_Base_v2,
            "AV_Base_v3": AV_Base_v3,
        }
        self.model = MODEL_MAP[args.model](args)

    def forward(self, batch):
        return self.model(batch)