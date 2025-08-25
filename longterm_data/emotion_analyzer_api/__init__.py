#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emotion Analyzer API package
Includes adapter classes for supported AI models.
"""

__version__ = "1.0.0"
__author__ = "Emotion Analyzer Team"

# Import only supported analyzers
try:
    from .emotion_analyzer_zhipu import EmotionAnalyzerZhipu
    from .emotion_analyzer_lenovo_qwen32b import EmotionAnalyzerLenovoQwen32b

    __all__ = [
        'EmotionAnalyzerZhipu',
        'EmotionAnalyzerLenovoQwen32b',
    ]
except ImportError as e:
    print(f"⚠️ Error importing AI model adapters: {e}")
    print("💡 Please ensure required dependencies are installed")
    __all__ = []