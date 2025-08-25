#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多功能Python工具集启动脚本
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查依赖包是否已安装"""
    required_packages = [
        'gradio', 'pandas', 'numpy', 'matplotlib', 
        'plotly', 'pillow', 'scikit-learn', 'opencv-python', 'wordcloud'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖包已安装")
    return True

def main():
    """主函数"""
    print("🚀 多功能Python工具集")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 检查主应用文件是否存在
    if not os.path.exists('main_app.py'):
        print("❌ 找不到 main_app.py 文件")
        print("请确保在正确的目录下运行此脚本")
        return
    
    print("\n🎯 启动应用...")
    print("📱 应用将在浏览器中打开")
    print("🌐 本地地址: http://localhost:7860")
    print("⏹️  按 Ctrl+C 停止应用")
    print("-" * 50)
    
    try:
        # 启动主应用
        subprocess.run([sys.executable, 'main_app.py'])
    except KeyboardInterrupt:
        print("\n\n👋 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动应用时出错: {e}")

if __name__ == "__main__":
    main()
