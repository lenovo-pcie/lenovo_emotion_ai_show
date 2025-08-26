import gradio as gr
import numpy as np
import cv2
import sys
import os
import time
import threading

# 集成情感识别模型
from emotion_recognition import predict_single_clip, load_prediction_model, load_feature_extractor

EMOTION_CLASS_MODEL_PATH = r"D:/emotion_model/AV_Base_v3/2025-07-22-14-04-04/best.pth"


sub_module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), './detection/det/'))
sys.path.append(sub_module_path)
from ultralytics import YOLO


# 全局只加载一次模型
emotion_model = load_prediction_model(EMOTION_CLASS_MODEL_PATH, gpu=0)
feat_model, video_processor = load_feature_extractor("clip-vit-large-patch14")

detector = YOLO('tab_realtime_emotion/weights/detector/model_11n.pt')

# 全局变量用于存储最近一次情绪结果
latest_emotion_text = "未检测到人脸"
latest_result_time = 0
emotion_lock = threading.Lock()
emotion_thread = None  # 标记当前是否有情绪识别线程在运行

def crop_face_yolo(frame, results):
    """根据YOLO检测结果裁剪人脸区域并返回224x224图片"""
    boxes = results[0].boxes.xyxy.cpu().numpy() if hasattr(results[0].boxes, 'xyxy') else []
    if len(boxes) == 0:
        return None
    x1, y1, x2, y2 = boxes[0].astype(int)
    face_img = frame[y1:y2, x1:x2]
    if face_img.size == 0:
        return None
    face_img = cv2.resize(face_img, (224, 224))
    return face_img

def async_appearance_predict(face_img):
    """异步处理人脸属性预测"""
    global latest_emotion_text, latest_result_time, emotion_thread
    try:
        face_info = {
            'bboxes': [[0, 0, 224, 224, 1.0]]  # 模拟人脸检测结果
        }
    except Exception as e:
        emotion_text = f"属性识别失败: {e}"
    with emotion_lock:
        latest_emotion_text = emotion_text
        latest_result_time = time.time()
        emotion_thread = None  # 标记线程已结束

def async_emotion_predict(face_img):
    global latest_emotion_text, latest_result_time, emotion_thread
    temp_path = "temp_face.jpg"
    cv2.imwrite(temp_path, face_img)
    try:
        result = predict_single_clip(
            clip_path=temp_path,
            model_path=None,  # 不再传路径
            model=emotion_model,  # 传已加载模型
            feat_model=feat_model,  # 传已加载特征提取模型
            processor=video_processor,  # 传已加载处理器
            gpu=0
        )
        # 输出结果
        print("\n===== 预测结果 =====")
        print(f"预测情感标签: {result['预测情感']}")
        print("各情感概率:")
        for emo, p in result["情感概率"].items():
            print(f"  {emo}: {p:.4f}")
        emotion_text = f"{result['预测情感']} ({result['置信度']:.2f})"
    except Exception as e:
        emotion_text = f"check failed: {e}"
    with emotion_lock:
        latest_emotion_text = emotion_text
        latest_result_time = time.time()
        emotion_thread = None  # 标记线程已结束

def process_frame(frame, detection_enabled_state):
    global latest_emotion_text, latest_result_time, emotion_thread
    if frame is None:
        return None

    display_frame = frame.copy()
    emotion_text = "without detection face"

    if detection_enabled_state:
        results = detector.predict(frame, verbose=False)
        display_frame = results[0].plot()
        face_img = crop_face_yolo(frame, results)
        now = time.time()
        # 只在没有线程运行且满足时间间隔时启动新线程
        if face_img is not None:
            with emotion_lock:
                emotion_text = latest_emotion_text
                last_time = latest_result_time
                thread_running = emotion_thread is not None
            if not thread_running and (now - last_time > 1):
                t = threading.Thread(target=async_emotion_predict, args=(face_img,), daemon=True)
                emotion_thread = t  # 正确赋值线程对象
                t.start()
        else:
            emotion_text = "without detection face"
        # 在画面左上角显示情绪
        cv2.rectangle(display_frame, (10, 10), (320, 60), (255,255,255), -1)
        cv2.putText(display_frame, emotion_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    else:
        cv2.rectangle(display_frame, (10, 10), (320, 60), (255,255,255), -1)
        cv2.putText(display_frame, "without detection", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

    
    return display_frame

def toggle_detection(current_state):
    new_state = not current_state
    new_button_text = "关闭人脸检测" if new_state else "开启人脸检测"
    return new_state, gr.Button(new_button_text)


def create_realtime_emotion_interface():
    """Create real-time emotion interface framework"""
    
    with gr.Blocks(title="实时情绪预览", theme=gr.themes.Soft()) as interface:
        detection_enabled = gr.State(False)
        with gr.Row():
            with gr.Column():
                input_video = gr.Image(sources=["webcam"], type="numpy", label="摄像头输入", streaming=True)
                toggle_button = gr.Button("开启人脸检测")
            with gr.Column():
                output_video = gr.Image(type="numpy", label="检测+情绪结果", streaming=True)

        toggle_button.click(
            toggle_detection,
            inputs=[detection_enabled],
            outputs=[detection_enabled, toggle_button]
        )

        input_video.stream(
            process_frame,
            inputs=[input_video, detection_enabled],
            outputs=output_video,
            stream_every= 0.1  # 每0.1秒处理一次帧
        )
        
        
    return interface




if __name__ == "__main__":
    interface = create_realtime_emotion_interface()
    interface.launch()
