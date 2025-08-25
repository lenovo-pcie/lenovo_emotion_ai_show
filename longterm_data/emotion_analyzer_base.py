import cv2
import sqlite3
import os
from datetime import datetime
from PIL import Image
import numpy as np
import base64
import io
import time
import signal
import sys
import threading
import multiprocessing
import json
import getpass

# 设置OpenCV日志级别，抑制调试信息
try:
    # 尝试不同的日志级别常量名称
    if hasattr(cv2, 'LOG_LEVEL_SILENT'):
        cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
    elif hasattr(cv2, 'utils_logging_setLogLevel'):
        cv2.utils_logging_setLogLevel(cv2.utils_logging.LOG_LEVEL_SILENT)
    elif hasattr(cv2, 'setLogLevel'):
        # 直接使用数字值
        cv2.setLogLevel(0)  # 0 = SILENT
    else:
        print("⚠️ 当前OpenCV版本不支持日志级别设置")
except Exception as e:
    print(f"⚠️ 设置OpenCV日志级别失败: {e}")

# 简化：不再依赖外部摄像头配置模块
def print_camera_config():
    pass

def get_system_camera_count():
    """简化：假定存在默认内置摄像头索引0"""
    return 1, [0]

class EmotionAnalyzerBase:
    def __init__(self, api_key, camera_backend=cv2.CAP_ANY, camera_index=0, model_name="Unknown"):
        """初始化情绪分析器基础类"""
        self.api_key = api_key
        self.camera_backend = camera_backend
        self.camera_index = camera_index
        self.model_name = model_name
        # Store database in the current working directory
        self.db_path = os.path.join(os.getcwd(), 'emotion_data.db')
        self.running = True
        self.init_database()
        
        # 设置信号处理，优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print(f"✅ {model_name}情绪分析器初始化完成")
        print(f"📷 摄像头索引: {self.camera_index}")
        print(f"🔧 摄像头后端: {self.camera_backend}")
        print(f"🗄️ 数据库: {self.db_path}")
    
    def signal_handler(self, signum, frame):
        """信号处理函数，用于优雅退出"""
        print(f"\n🛑 收到退出信号 {signum}，正在停止程序...")
        self.running = False
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emotion_records'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # 检查是否有emotion_level字段
            cursor.execute("PRAGMA table_info(emotion_records)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'emotion_level' not in columns:
                print("🔄 检测到旧版本数据库，正在添加emotion_level字段...")
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN emotion_level REAL DEFAULT 0.0')
                print("✅ emotion_level字段添加完成")
            
            # 检查是否有屏幕内容相关字段
            if 'app_name' not in columns:
                print("🔄 检测到旧版本数据库，正在添加屏幕内容字段...")
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN app_name TEXT DEFAULT "未知应用"')
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN app_category TEXT DEFAULT "其他"')
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN content_description TEXT DEFAULT "无法识别当前应用和内容"')
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN screen_path TEXT')
                print("✅ 屏幕内容字段添加完成")
        else:
            # 新建表时直接带所有字段
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emotion_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    emotion TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    has_face BOOLEAN NOT NULL,
                    image_path TEXT,
                    username TEXT,
                    emotion_level REAL DEFAULT 0.0,
                    app_name TEXT DEFAULT "未知应用",
                    app_category TEXT DEFAULT "其他",
                    content_description TEXT DEFAULT "无法识别当前应用和内容",
                    screen_path TEXT
                )
            ''')
        conn.commit()
        conn.close()
    
    def save_image(self, image, timestamp, image_index=None):
        """保存图像到本地，目录结构为 年/月/日/小时/"""
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        # 获取当前目录的父目录
        parent_dir = os.path.dirname(os.path.abspath('.'))
        dir_path = os.path.join(
            parent_dir,
            'testimages',
            dt.strftime('%Y'),
            dt.strftime('%m'),
            dt.strftime('%d'),
            dt.strftime('%H')
        )
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        # 如果有图片序号，添加到文件名中
        if image_index is not None:
            filename = f'{timestamp}_{image_index:02d}.jpg'
        else:
            filename = f'{timestamp}.jpg'
            
        image_path = os.path.join(dir_path, filename)
        cv2.imwrite(image_path, image)
        return image_path
    
    def image_to_base64(self, image):
        """将OpenCV图像转换为base64字符串"""
        # 转换BGR到RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # 转换为base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return img_str
    
    def capture_screen(self, timestamp):
        """捕获屏幕截图"""
        try:
            import pyautogui
            print(f"🖥️ 正在捕获屏幕截图...")
            
            # 捕获屏幕截图
            screenshot = pyautogui.screenshot()
            
            # 转换为OpenCV格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 保存截图
            saved_screen_path = self.save_screen(screenshot_cv, timestamp)
            
            print(f"✅ 屏幕截图已保存到: {saved_screen_path}")
            return screenshot_cv, saved_screen_path
            
        except ImportError:
            print("❌ 未安装pyautogui，无法捕获屏幕截图")
            return None, None
        except Exception as e:
            print(f"❌ 屏幕截图捕获失败: {e}")
            return None, None
    
    def save_screen(self, screen_image, timestamp):
        """保存屏幕截图到本地，与视频保存到相同路径"""
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        # 获取当前目录的父目录
        parent_dir = os.path.dirname(os.path.abspath('.'))
        dir_path = os.path.join(
            parent_dir,
            'testvideos',  # 使用与视频相同的目录存储屏幕截图
            dt.strftime('%Y'),
            dt.strftime('%m'),
            dt.strftime('%d'),
            dt.strftime('%H')
        )
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        filename = f'{timestamp}_screen.png'
        screen_path = os.path.join(dir_path, filename)
        cv2.imwrite(screen_path, screen_image)
        return screen_path
    
    def analyze_emotion(self, images):
        """分析情绪 - 子类必须实现此方法，接收图片列表"""
        raise NotImplementedError("子类必须实现analyze_emotion方法")
    
    def _get_default_result(self):
        """获取默认结果"""
        return {
            "has_face": False,
            "emotion": "无",
            "confidence": 0.0,
            "emotion_level": 0.0
        }
    
    def _get_default_screen_result(self):
        """获取默认的屏幕分析结果"""
        return {
            "app_name": "未知应用",
            "app_category": "其他",
            "content_description": "无法识别当前应用和内容"
        }
    
    def save_to_database(self, timestamp, emotion, confidence, has_face, image_path=None, emotion_level=0.0, 
                        app_name="未知应用", app_category="其他", content_description="无法识别当前应用和内容", screen_path=None):
        """保存分析结果到数据库，增加屏幕内容字段"""
        username = None
        try:
            username = getpass.getuser()
        except Exception:
            username = os.environ.get('USERNAME') or os.environ.get('USER') or 'unknown'
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO emotion_records (timestamp, emotion, confidence, has_face, image_path, username, emotion_level, 
                                       app_name, app_category, content_description, screen_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, emotion, confidence, has_face, image_path, username, emotion_level, 
              app_name, app_category, content_description, screen_path))
        conn.commit()
        conn.close()
    
    def capture_video(self, duration=3.0):
        """从摄像头录制指定时长的视频"""
        import cv2
        import tempfile
        import os
        
        print(f"🎬 开始录制 {duration} 秒视频...")
        
        # 打开摄像头
        cap = cv2.VideoCapture(self.camera_index, self.camera_backend)
        if not cap.isOpened():
            raise Exception(f"无法打开摄像头 {self.camera_index}")
        
        # 获取摄像头参数
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30  # 默认帧率
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 创建临时视频文件
        temp_video_path = tempfile.mktemp(suffix='.mp4')
        
        # 设置视频编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            cap.release()
            raise Exception("无法创建视频文件")
        
        # 计算需要录制的帧数
        total_frames = int(fps * duration)
        frame_count = 0
        
        try:
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    print(f"⚠️ 第 {frame_count + 1} 帧读取失败")
                    break
                
                # 写入视频帧
                out.write(frame)
                frame_count += 1
                
                # 显示录制进度
                if frame_count % fps == 0:
                    elapsed_time = frame_count / fps
                    print(f"   📹 已录制 {elapsed_time:.1f}/{duration} 秒")
        
        finally:
            # 释放资源
            cap.release()
            out.release()
        
        print(f"✅ 视频录制完成: {frame_count} 帧, {frame_count/fps:.2f} 秒")
        return temp_video_path
    
    def video_to_base64(self, video_path):
        """将视频文件转换为base64字符串"""
        import base64
        
        try:
            with open(video_path, 'rb') as video_file:
                video_data = video_file.read()
                video_base64 = base64.b64encode(video_data).decode('utf-8')
                return video_base64
        except Exception as e:
            raise Exception(f"视频文件读取失败: {e}")
    
    def extract_frames_from_video(self, video_path, num_frames=6):
        """从视频中提取指定数量的帧"""
        import cv2
        
        print(f"🎬 从视频中提取 {num_frames} 帧图像...")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")
        
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps
        
        print(f"📊 视频信息: {total_frames} 帧, {fps:.1f} fps, {duration:.2f} 秒")
        
        # 计算提取帧的间隔
        if total_frames <= num_frames:
            # 如果总帧数少于需要的帧数，提取所有帧
            frame_indices = list(range(total_frames))
        else:
            # 平均间隔提取帧
            step = total_frames / num_frames
            frame_indices = [int(i * step) for i in range(num_frames)]
        
        frames = []
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
                print(f"   ✅ 提取第 {i+1}/{num_frames} 帧 (原始帧 {frame_idx})")
            else:
                print(f"   ❌ 提取第 {i+1}/{num_frames} 帧失败")
        
        cap.release()
        
        if not frames:
            raise Exception("未能从视频中提取到任何帧")
        
        print(f"✅ 成功提取 {len(frames)} 帧图像")
        return frames
    
    def analyze_video_emotion(self, video_path):
        """分析视频中的情绪 - 从视频中提取6帧图像，传给模型分析"""
        try:
            print(f"🎬 正在从视频中提取6帧图像...")
            
            # 从视频中提取6帧
            frames = self.extract_frames_from_video(video_path, num_frames=6)
            
            print(f"📊 成功提取 {len(frames)} 帧图像")
            
            # 将帧图像传给模型进行分析
            analysis_results = self.analyze_emotion(frames)
            
            print(f"📊 模型返回了 {len(analysis_results)} 个分析结果")
            for i, result in enumerate(analysis_results):
                print(f"   ✅ 第 {i+1} 个结果: {result['emotion']} (级别: {result['emotion_level']:.2f})")
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ 视频分析失败: {e}")
            return [self._get_default_result() for _ in range(6)]
    
    def _calculate_average_result(self, results):
        """计算多个分析结果的平均值"""
        if not results:
            return self._get_default_result()
        
        # 统计情绪类型
        emotion_counts = {}
        total_confidence = 0
        total_emotion_level = 0
        total_has_face = 0
        
        for result in results:
            emotion = result.get('emotion', '无')
            confidence = result.get('confidence', 0.0)
            emotion_level = result.get('emotion_level', 0.0)
            has_face = result.get('has_face', False)
            
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            total_confidence += confidence
            total_emotion_level += emotion_level
            if has_face:
                total_has_face += 1
        
        # 选择出现次数最多的情绪
        if emotion_counts:
            most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])
            dominant_emotion = most_common_emotion[0]
        else:
            dominant_emotion = '无'
        
        # 计算平均值
        avg_confidence = total_confidence / len(results)
        avg_emotion_level = total_emotion_level / len(results)
        avg_has_face = total_has_face / len(results) > 0.5  # 超过一半的帧有人脸
        
        return {
            "has_face": avg_has_face,
            "emotion": dominant_emotion,
            "confidence": avg_confidence,
            "emotion_level": avg_emotion_level
        }
    
    def process_video_capture(self):
        """完整的视频捕获和分析流程"""
        try:
            # 记录总体开始时间
            total_start_time = time.time()
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # 录制视频
            print(f"[{timestamp}] 正在录制视频...")
            capture_start = time.time()
            video_path = self.capture_video(duration=3.0)
            capture_time = time.time() - capture_start
            print(f"[{timestamp}] 视频录制完成 - 耗时: {capture_time:.2f}秒")
            
            # 捕获屏幕截图
            print(f"[{timestamp}] 正在捕获屏幕截图...")
            screen_start = time.time()
            screen_image, screen_path = self.capture_screen(timestamp)
            screen_time = time.time() - screen_start
            print(f"[{timestamp}] 屏幕截图完成 - 耗时: {screen_time:.2f}秒")
            
            # 分析视频情绪
            print(f"[{timestamp}] 正在分析视频情绪...")
            analysis_start = time.time()
            analysis_results = self.analyze_video_emotion(video_path)
            analysis_time = time.time() - analysis_start
            print(f"[{timestamp}] 视频情绪分析完成 - 耗时: {analysis_time:.2f}秒")
            
            # 分析屏幕内容（如果支持）
            screen_analysis_result = None
            if screen_image is not None and hasattr(self, 'analyze_screen_content'):
                print(f"[{timestamp}] 正在分析屏幕内容...")
                screen_analysis_start = time.time()
                try:
                    screen_analysis_result = self.analyze_screen_content(screen_image)
                    screen_analysis_time = time.time() - screen_analysis_start
                    print(f"[{timestamp}] 屏幕内容分析完成 - 耗时: {screen_analysis_time:.2f}秒")
                except Exception as e:
                    print(f"[{timestamp}] 屏幕内容分析失败: {e}")
                    screen_analysis_result = self._get_default_screen_result()
            else:
                screen_analysis_result = self._get_default_screen_result()
            
            # 保存视频文件
            print(f"[{timestamp}] 正在保存视频...")
            save_start = time.time()
            saved_video_path = self.save_video(video_path, timestamp)
            save_time = time.time() - save_start
            print(f"[{timestamp}] 视频已保存到: {saved_video_path} - 耗时: {save_time:.2f}秒")
            
            # 保存到数据库 - 处理6个分析结果
            db_start = time.time()
            saved_results = []
            
            for i, analysis_result in enumerate(analysis_results):
                # 为每个结果生成唯一的时间戳
                result_timestamp = f"{timestamp}_{i:02d}"
                
                # 保存到数据库，包含屏幕内容信息
                self.save_to_database(
                    timestamp=result_timestamp,
                    emotion=analysis_result['emotion'],
                    confidence=analysis_result['confidence'],
                    has_face=analysis_result['has_face'],
                    image_path=saved_video_path,  # 使用视频路径替代图片路径
                    emotion_level=analysis_result['emotion_level'],
                    app_name=screen_analysis_result.get('app_name', '未知应用'),
                    app_category=screen_analysis_result.get('app_category', '其他'),
                    content_description=screen_analysis_result.get('content_description', '无法识别当前应用和内容'),
                    screen_path=screen_path
                )
                
                saved_results.append({
                    'timestamp': result_timestamp,
                    'result': analysis_result,
                    'screen_analysis': screen_analysis_result
                })
                
                # 打印每个结果的详细信息
                emotion_info = f"情绪={analysis_result['emotion']}"
                if analysis_result['has_face'] and analysis_result['emotion'] != '无':
                    emotion_info += f", 级别={analysis_result['emotion_level']:.2f}"
                print(f"[{timestamp}] 结果 {i+1}/6: 人脸={analysis_result['has_face']}, {emotion_info}, 置信度={analysis_result['confidence']:.2f}")
            
            # 打印屏幕分析结果
            if screen_analysis_result:
                print(f"[{timestamp}] 屏幕分析: 应用={screen_analysis_result.get('app_name', '未知')}, "
                      f"分类={screen_analysis_result.get('app_category', '其他')}, "
                      f"描述={screen_analysis_result.get('content_description', '无描述')}")
            
            db_time = time.time() - db_start
            print(f"[{timestamp}] 数据保存完成 - 耗时: {db_time:.2f}秒")
            
            # 计算总耗时
            total_time = time.time() - total_start_time
            
            print(f"[{timestamp}] 视频和屏幕分析完成！")
            print(f"[{timestamp}] 总处理时间: {total_time:.2f}秒")
            print(f"[{timestamp}] 性能优化: 视频分析在保存前完成，节省了先保存再读取的时间")
            print(f"[{timestamp}] 从视频中提取6帧并返回6个分析结果")
            print(f"[{timestamp}] 同时分析屏幕内容并保存到同一条记录")
            
            # 清理临时文件
            try:
                os.remove(video_path)
            except:
                pass
            
            return {
                'timestamp': timestamp,
                'analysis_results': saved_results,
                'video_path': saved_video_path,
                'screen_path': screen_path,
                'screen_analysis': screen_analysis_result,
                'timing': {
                    'capture': capture_time,
                    'screen': screen_time,
                    'analysis': analysis_time,
                    'save': save_time,
                    'database': db_time,
                    'total': total_time
                }
            }
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y%m%d-%H%M%S')}] 视频处理过程中出现错误: {e}")
            return None
    
    def save_video(self, video_path, timestamp):
        """保存视频到本地，目录结构为 年/月/日/小时/"""
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        # 获取当前目录的父目录
        parent_dir = os.path.dirname(os.path.abspath('.'))
        dir_path = os.path.join(
            parent_dir,
            'testvideos',  # 使用testvideos目录存储视频
            dt.strftime('%Y'),
            dt.strftime('%m'),
            dt.strftime('%d'),
            dt.strftime('%H')
        )
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        filename = f'{timestamp}_video.mp4'
        saved_video_path = os.path.join(dir_path, filename)
        
        # 复制视频文件
        import shutil
        shutil.copy2(video_path, saved_video_path)
        return saved_video_path

    def run_continuous_video(self, interval_minutes=1.0):
        """连续运行模式 - 视频识别版本"""
        print("🚀 情绪分析系统启动 - 视频识别模式")
        print(f"🤖 使用模型: {self.model_name}")
        print(f"📷 摄像头索引: {self.camera_index}")
        print(f"⏰ 捕获间隔: {interval_minutes} 分钟")
        print(f"🎬 每次录制: 3秒视频")
        print("🛑 按 Ctrl+C 停止程序")
        print("="*60)
        
        interval_seconds = int(interval_minutes * 60)  # 转换为整数
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n🔄 第 {cycle_count} 次循环 - {current_time}")
                print("-" * 40)
                
                # 执行视频捕获和分析
                result = self.process_video_capture()
                
                if result:
                    print(f"✅ 第 {cycle_count} 次循环完成")
                else:
                    print(f"❌ 第 {cycle_count} 次循环失败")
                
                # 如果不是最后一次循环，则等待
                if self.running:
                    print(f"⏳ 等待 {interval_minutes} 分钟后进行下一次录制...")
                    print(f"🕐 下次录制时间: {datetime.fromtimestamp(time.time() + interval_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 分段等待，每5秒检查一次是否需要退出
                    for i in range(interval_seconds):
                        if not self.running:
                            break
                        time.sleep(1)
                        
                        # 每5秒显示一次倒计时
                        if (i + 1) % 5 == 0:
                            remaining = interval_seconds - (i + 1)
                            print(f"⏰ 剩余等待时间: {remaining} 秒")
                
            except KeyboardInterrupt:
                print("\n🛑 用户中断程序")
                self.running = False
                break
            except Exception as e:
                print(f"❌ 循环过程中出现错误: {e}")
                print("🔄 5秒后重试...")
                time.sleep(5)
        
        print("\n👋 程序已停止")
        print(f"📊 总共完成了 {cycle_count} 次视频分析循环")

def try_open_camera(index, backend, result_dict):
    import cv2
    try:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                result_dict['success'] = True
                result_dict['width'] = width
                result_dict['height'] = height
                result_dict['fps'] = fps
        cap.release()
    except Exception:
        pass

def detect_cameras():
    """简化：仅返回默认内置摄像头（索引0）"""
    return [{
        'index': 0,
        'backend': cv2.CAP_ANY,
        'backend_name': 'Auto',
        'resolution': 'Auto',
        'fps': 30.0,
        'is_external': False,
        'display_name': '默认内置摄像头'
    }]

def select_camera():
    """简化：直接返回默认内置摄像头（索引0）"""
    return {
        'index': 0,
        'backend': cv2.CAP_ANY,
        'backend_name': 'Auto',
        'resolution': 'Auto',
        'fps': 30.0,
        'is_external': False,
        'display_name': '默认内置摄像头'
    }