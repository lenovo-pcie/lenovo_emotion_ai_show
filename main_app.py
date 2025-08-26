import gradio as gr
import os
import sys

# Add subdirectories to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tab_emotion_battery'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tab_realtime_emotion'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tab_data_analysis'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tab_image_processing'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tab_audio_processing'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tab_text_analysis'))

# Import submodules
emotion_battery_available = False
realtime_emotion_available = False
data_visualization_available = False
image_editor_available = False
audio_processor_available = False
text_processor_available = False

try:
    from emotion_battery_interface import create_emotion_battery_interface
    emotion_battery_available = True
    print("✅ Emotion battery module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import emotion battery module: {e}")

try:
    from realtime_emotion_interface import create_realtime_emotion_interface
    realtime_emotion_available = True
    print("✅ Realtime emotion module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import realtime emotion module: {e}")

try:
    from data_visualization import create_data_visualization_interface
    data_visualization_available = True
    print("✅ Data visualization module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import data visualization module: {e}")

try:
    from image_editor import create_image_editor_interface
    image_editor_available = True
    print("✅ Image processing module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import image processing module: {e}")

try:
    from audio_processor import create_audio_processor_interface
    audio_processor_available = True
    print("✅ Audio processing module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import audio processing module: {e}")

try:
    from text_processor import create_text_processor_interface
    text_processor_available = True
    print("✅ Text analysis module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import text analysis module: {e}")

def create_main_interface():
    """Create main interface with multiple tabs"""
    
    # Create interfaces for each subpage
    if emotion_battery_available:
        try:
            emotion_battery_tab = create_emotion_battery_interface()
        except Exception as e:
            print(f"Error creating emotion battery interface: {e}")
            emotion_battery_tab = gr.Interface(
                fn=lambda: "Emotion battery module failed to load",
                inputs=None,
                outputs="text",
                title="Emotion Battery",
                description="Module failed to load, please check code"
            )
    else:
        emotion_battery_tab = gr.Interface(
            fn=lambda: "Emotion battery module not installed",
            inputs=None,
            outputs="text",
            title="Emotion Battery",
            description="Please install required dependencies"
        )
    
    if realtime_emotion_available:
        try:
            realtime_emotion_tab = create_realtime_emotion_interface()
        except Exception as e:
            print(f"Error creating realtime emotion interface: {e}")
            realtime_emotion_tab = gr.Interface(
                fn=lambda: "Realtime emotion module failed to load",
                inputs=None,
                outputs="text",
                title="Realtime Emotion",
                description="Module failed to load, please check code"
            )
    else:
        realtime_emotion_tab = gr.Interface(
            fn=lambda: "Realtime emotion module not installed",
            inputs=None,
            outputs="text",
            title="Realtime Emotion",
            description="Please install required dependencies"
        )
    
    if data_visualization_available:
        try:
            data_tab = create_data_visualization_interface()
        except Exception as e:
            print(f"Error creating data visualization interface: {e}")
            data_tab = gr.Interface(
                fn=lambda: "Data visualization module failed to load",
                inputs=None,
                outputs="text",
                title="Data Visualization",
                description="Module failed to load, please check code"
            )
    else:
        data_tab = gr.Interface(
            fn=lambda: "Data visualization module not installed",
            inputs=None,
            outputs="text",
            title="Data Visualization",
            description="Please install required dependencies"
        )
    
    if image_editor_available:
        try:
            image_tab = create_image_editor_interface()
        except Exception as e:
            print(f"Error creating image processing interface: {e}")
            image_tab = gr.Interface(
                fn=lambda: "Image processing module failed to load",
                inputs=None,
                outputs="text",
                title="Image Processing",
                description="Module failed to load, please check code"
            )
    else:
        image_tab = gr.Interface(
            fn=lambda: "Image processing module not installed",
            inputs=None,
            outputs="text",
            title="Image Processing",
            description="Please install required dependencies"
        )
    
    if audio_processor_available:
        try:
            audio_tab = create_audio_processor_interface()
        except Exception as e:
            print(f"Error creating audio processing interface: {e}")
            audio_tab = gr.Interface(
                fn=lambda: "Audio processing module failed to load",
                inputs=None,
                outputs="text",
                title="Audio Processing",
                description="Module failed to load, please check code"
            )
    else:
        audio_tab = gr.Interface(
            fn=lambda: "Audio processing module not installed",
            inputs=None,
            outputs="text",
            title="Audio Processing",
            description="Please install required dependencies"
        )
    
    if text_processor_available:
        try:
            text_tab = create_text_processor_interface()
        except Exception as e:
            print(f"Error creating text analysis interface: {e}")
            text_tab = gr.Interface(
                fn=lambda: "Text analysis module failed to load",
                inputs=None,
                outputs="text",
                title="Text Analysis",
                description="Module failed to load, please check code"
            )
    else:
        text_tab = gr.Interface(
            fn=lambda: "Text analysis module not installed",
            inputs=None,
            outputs="text",
            title="Text Analysis",
            description="Please install required dependencies"
        )
    
    # Create main interface with multiple tabs
    with gr.Blocks(title="Lenovo Emotion AI", theme=gr.themes.Soft()) as main_interface:
        gr.Markdown("# 🚀 Lenovo Emotion AI")
        gr.Markdown("This is a Python application integrating multiple functions, each tab corresponding to different functional modules.")
        
        with gr.Tabs():
            with gr.TabItem("🔋 Emotion Battery", id=0):
                emotion_battery_tab.render()
            
            with gr.TabItem("📡 实时情绪预览", id=1):
                realtime_emotion_tab.render()
            
            with gr.TabItem("📊 Data Visualization", id=2):
                data_tab.render()
            
            with gr.TabItem("🖼️ Image Processing", id=3):
                image_tab.render()
            
            with gr.TabItem("🎵 Audio Processing", id=4):
                audio_tab.render()
            
            with gr.TabItem("📝 Text Analysis", id=5):
                text_tab.render()
        
        # gr.Markdown("---")
        # gr.Markdown("### 📁 Project Structure")
        # gr.Markdown("""
        # - `Emotion Battery` - Emotion battery module
        # - `Realtime Emotion` - Real-time emotion module
        # - `data_analysis/` - Data analysis and visualization module
        # - `image_processing/` - Image processing module
        # - `audio_processing/` - Audio processing module
        # - `text_analysis/` - Text analysis module
        # """)
        
    
    return main_interface

if __name__ == "__main__":
    # Create and launch application
    app = create_main_interface()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,  # Use port 7861
        share=False,
        show_error=True,
        quiet=False
    )
