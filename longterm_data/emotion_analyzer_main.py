#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emotion Analysis System - Main Program (test)
Supported models (current selection trimmed in code): Zhipu (cloud), Lenovo-Qwen32b (remote)
"""

import sys
import importlib
import cv2

def select_model():
    """Select AI model"""
    models = [
        {"id": "1", "name": "Zhipu", "description": "Zhipu GLM-4V (cloud)", "module": "emotion_analyzer_api.emotion_analyzer_zhipu", "class": "EmotionAnalyzerZhipu"},
        {"id": "2", "name": "Lenovo-Qwen32b", "description": "Lenovo remote service (Ollama, qwen2.5vl:32b)", "module": "emotion_analyzer_api.emotion_analyzer_lenovo_qwen32b", "class": "EmotionAnalyzerLenovoQwen32b"}
    ]
    
    print("🤖 Emotion Analysis System - Model Selection")
    print("="*50)
    print("Please choose an AI model:")
    print()
    
    for model in models:
        print(f"{model['id']}. {model['name']} - {model['description']}")
    
    print()
    
    while True:
        try:
            choice = input("Enter model number: ").strip()
            if choice in [model['id'] for model in models]:
                selected_model = next(model for model in models if model['id'] == choice)
                print(f"✅ Selected: {selected_model['name']}")
                return selected_model
            else:
                print("❌ Invalid choice, please enter a valid number")
        except KeyboardInterrupt:
            print("\n🛑 Selection cancelled by user")
            return None
        except ValueError:
            print("❌ Please enter a valid number")

def get_api_key(model_name):
    """Get API key"""
    # Default API keys
    default_keys = {
        "Zhipu": "a1e9d780009040fa85bf20b53c810744.7mWfNxsSrKSgMoTD",
        "Lenovo-Qwen32b": "LNV-666d8c88c76a00ed2c2f3128bcbb20f4"
    }
    
    default_key = default_keys.get(model_name, "")
    
    print(f"\n🔑 Enter API key for {model_name}:")
    if default_key:
        print(f"💡 Tip: Press Enter to use the default key, or input a new one")
        print(f"   Default key: {default_key[:10]}...")
    else:
        print("💡 Tip:")
    
    if model_name == "Zhipu":
        print("   - Visit https://open.bigmodel.cn/usercenter/apikeys")
        print("   - Create an API key")
    elif model_name == "Lenovo-Qwen32b":
        print("   - Remote Ollama service is configured")
        print("   - Server: 211.93.18.61:33434")
        print("   - Model: qwen2.5vl:32b")
        print("   - API key is preset")
    
    
    while True:
        try:
            if model_name == "Lenovo-Qwen32b":
                api_key = input("API key (press Enter to use preset): ").strip()
                if not api_key:
                    api_key = "LNV-666d8c88c76a00ed2c2f3128bcbb20f4"
                    print("✅ Using preset API key")
            
            # No other models currently require address prompts
            else:
                api_key = input("API key: ").strip()
                if not api_key and default_key:
                    api_key = default_key
                    print(f"✅ Using default API key: {default_key[:10]}...")
            if api_key:
                return api_key
            else:
                print("❌ Input cannot be empty")
        except KeyboardInterrupt:
            print("\n🛑 Input cancelled by user")
            return None

def get_interval():
    """Get capture interval"""
    print(f"\n⏰ Set capture interval:")
    try:
        interval = float(input("Enter interval in minutes (default 1.0): ") or "1.0")
        if interval < 0.1:
            print("⚠️ Interval too short, set to 0.1 minutes")
            interval = 0.1
        return interval
    except ValueError:
        print("⚠️ Using default interval: 1.0 minutes")
        return 1.0

def main():
    """Main entry"""
    print("😊 Emotion Analysis System")
    print("="*50)
    
    # Video-only mode
    print("Currently supports: Video recognition mode (record 3 seconds)")
    recognition_mode = "video"
    
    # Select model
    selected_model = select_model()
    if selected_model is None:
        print("❌ No model selected, exiting")
        return
    
    # Get API key
    api_key = get_api_key(selected_model['name'])
    if api_key is None:
        print("❌ No API key provided, exiting")
        return
    
    # Import selected model module
    try:
        module = importlib.import_module(selected_model['module'])
        analyzer_class = getattr(module, selected_model['class'])
    except ImportError as e:
        print(f"❌ Failed to import model module: {e}")
        print(f"💡 Ensure {selected_model['module']}.py exists")
        return
    except AttributeError as e:
        print(f"❌ Model class not found: {e}")
        return
    
    # 使用默认内置摄像头（索引0，自动选择后端）
    # 获取捕获间隔
    interval = get_interval()
    
    # Create analyzer (using default camera settings)
    try:
        analyzer = analyzer_class(
            api_key=api_key,
            camera_backend=cv2.CAP_ANY,
            camera_index=0
        )
        print("✅ Analyzer initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize analyzer: {e}")
        return
    
    # Run video mode only
    try:
        analyzer.run_continuous_video(interval)
    except Exception as e:
        print(f"❌ Error during execution: {e}")
    finally:
        print("\n🏁 Emotion analysis finished")

if __name__ == "__main__":
    main() 