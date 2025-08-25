#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪分析系统主程序test
支持多种AI模型：Gemini、Zhipu、Qwen、DeepSeek
"""

import sys
import importlib
import cv2

def select_model():
    """选择AI模型"""
    models = [
        {"id": "1", "name": "Zhipu", "description": "智谱AI GLM-4V (云端)", "module": "emotion_analyzer_api.emotion_analyzer_zhipu", "class": "EmotionAnalyzerZhipu"},
        {"id": "2", "name": "Lenovo-Qwen32b", "description": "联想远程服务 (Ollama, qwen2.5vl:32b)", "module": "emotion_analyzer_api.emotion_analyzer_lenovo_qwen32b", "class": "EmotionAnalyzerLenovoQwen32b"}
    ]
    
    print("🤖 情绪分析系统 - 模型选择")
    print("="*50)
    print("请选择要使用的AI模型：")
    print()
    
    for model in models:
        print(f"{model['id']}. {model['name']} - {model['description']}")
    
    print()
    
    while True:
        try:
            choice = input("请输入模型编号 : ").strip()
            if choice in [model['id'] for model in models]:
                selected_model = next(model for model in models if model['id'] == choice)
                print(f"✅ 已选择: {selected_model['name']}")
                return selected_model
            else:
                print("❌ 无效选择，请输入一个有效数字")
        except KeyboardInterrupt:
            print("\n🛑 用户取消选择")
            return None
        except ValueError:
            print("❌ 请输入有效的数字")

def get_api_key(model_name):
    """获取API密钥"""
    # 默认API密钥
    default_keys = {
        "Zhipu": "a1e9d780009040fa85bf20b53c810744.7mWfNxsSrKSgMoTD",
        "Lenovo-Qwen32b": "LNV-666d8c88c76a00ed2c2f3128bcbb20f4"
    }
    
    default_key = default_keys.get(model_name, "")
    
    print(f"\n🔑 请输入 {model_name} 的API密钥:")
    if default_key:
        print(f"💡 提示：直接回车使用默认密钥，或输入新的密钥")
        print(f"   默认密钥: {default_key[:10]}...")
    else:
        print("💡 提示：")
    
    if model_name == "Zhipu":
        print("   - 访问 https://open.bigmodel.cn/usercenter/apikeys")
        print("   - 创建API密钥")
    elif model_name == "Lenovo-Qwen32b":
        print("   - 远程Ollama服务已配置")
        print("   - 服务器地址: 211.93.18.61:33434")
        print("   - 模型: qwen2.5vl:32b")
        print("   - API密钥已预设")
    
    
    while True:
        try:
            if model_name == "Lenovo-Qwen32b":
                api_key = input("API密钥 (默认已配置): ").strip()
                if not api_key:
                    api_key = "LNV-666d8c88c76a00ed2c2f3128bcbb20f4"
                    print("✅ 使用预设API密钥")
            
            elif model_name == "Ollama-Qwen":
                api_key = input("Ollama服务地址 (默认: 192.168.1.156): ").strip()
                if not api_key:
                    api_key = "192.168.1.156"
                    print("✅ 使用默认服务器地址: 192.168.1.156")
            elif model_name == "Ollama-Qwen-32B":
                api_key = input("Ollama服务地址 (默认: 127.0.0.1): ").strip()
                if not api_key:
                    api_key = "127.0.0.1"
                    print("✅ 使用默认服务器地址: 127.0.0.1")
            else:
                api_key = input("API密钥: ").strip()
                if not api_key and default_key:
                    api_key = default_key
                    print(f"✅ 使用默认API密钥: {default_key[:10]}...")
            if api_key:
                return api_key
            else:
                print("❌ 输入不能为空")
        except KeyboardInterrupt:
            print("\n🛑 用户取消输入")
            return None

def get_interval():
    """获取捕获间隔"""
    print(f"\n⏰ 设置捕获间隔:")
    try:
        interval = float(input("请输入捕获间隔分钟数 (默认1分钟): ") or "1.0")
        if interval < 0.1:
            print("⚠️ 间隔时间太短，设置为0.1分钟")
            interval = 0.1
        return interval
    except ValueError:
        print("⚠️ 使用默认间隔: 1.0分钟")
        return 1.0

def main():
    """主函数"""
    print("😊 情绪分析系统")
    print("="*50)
    
    # 只保留视频识别模式
    print("当前仅支持：视频识别模式 (录制3秒视频)")
    recognition_mode = "video"
    
    # 选择模型
    selected_model = select_model()
    if selected_model is None:
        print("❌ 未选择模型，程序退出")
        return
    
    # 获取API密钥
    api_key = get_api_key(selected_model['name'])
    if api_key is None:
        print("❌ 未提供API密钥，程序退出")
        return
    
    # 导入选中的模型模块
    try:
        module = importlib.import_module(selected_model['module'])
        analyzer_class = getattr(module, selected_model['class'])
    except ImportError as e:
        print(f"❌ 导入模型模块失败: {e}")
        print(f"💡 请确保 {selected_model['module']}.py 文件存在")
        return
    except AttributeError as e:
        print(f"❌ 模型类不存在: {e}")
        return
    
    # 使用默认内置摄像头（索引0，自动选择后端）
    # 获取捕获间隔
    interval = get_interval()
    
    # 创建分析器实例（使用默认摄像头设置）
    try:
        analyzer = analyzer_class(
            api_key=api_key,
            camera_backend=cv2.CAP_ANY,
            camera_index=0
        )
        print("✅ 分析器初始化成功")
    except Exception as e:
        print(f"❌ 分析器初始化失败: {e}")
        return
    
    # 只运行视频模式
    try:
        analyzer.run_continuous_video(interval)
    except Exception as e:
        print(f"❌ 运行过程中出现错误: {e}")
    finally:
        print("\n🏁 情绪分析结束")

if __name__ == "__main__":
    main() 