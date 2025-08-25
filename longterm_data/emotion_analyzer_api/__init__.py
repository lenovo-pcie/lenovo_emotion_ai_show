#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪分析API模块包
包含各种AI模型的适配器类
"""

__version__ = "1.0.0"
__author__ = "Emotion Analyzer Team"

# 尝试导入所有可用的分析器类
try:
    from .emotion_analyzer_gemini import EmotionAnalyzerGemini
    from .emotion_analyzer_zhipu import EmotionAnalyzerZhipu
    from .emotion_analyzer_qwen import EmotionAnalyzerQwen
    from .emotion_analyzer_deepseek import EmotionAnalyzerDeepSeek
    
    __all__ = [
        'EmotionAnalyzerGemini',
        'EmotionAnalyzerZhipu', 
        'EmotionAnalyzerQwen',
        'EmotionAnalyzerDeepSeek'
    ]
except ImportError as e:
    print(f"⚠️ 导入AI模型适配器时出现错误: {e}")
    print("💡 请确保已安装所需的依赖包")
    __all__ = [] 