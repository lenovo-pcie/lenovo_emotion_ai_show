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

# Set OpenCV log level to suppress debug output
try:
    # Try different constant names across versions
    if hasattr(cv2, 'LOG_LEVEL_SILENT'):
        cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
    elif hasattr(cv2, 'utils_logging_setLogLevel'):
        cv2.utils_logging_setLogLevel(cv2.utils_logging.LOG_LEVEL_SILENT)
    elif hasattr(cv2, 'setLogLevel'):
        # 直接使用数字值
        cv2.setLogLevel(0)  # 0 = SILENT
    else:
        print("⚠️ Current OpenCV version does not support setting log level")
except Exception as e:
    print(f"⚠️ Failed to set OpenCV log level: {e}")

# Simplified: no dependency on external camera config module
def print_camera_config():
    pass

def get_system_camera_count():
    """Simplified: assume default internal camera at index 0"""
    return 1, [0]

class EmotionAnalyzerBase:
    def __init__(self, api_key, camera_backend=cv2.CAP_ANY, camera_index=0, model_name="Unknown"):
        """Initialize emotion analyzer base class"""
        self.api_key = api_key
        self.camera_backend = camera_backend
        self.camera_index = camera_index
        self.model_name = model_name
        # Store database in the current working directory
        self.db_path = os.path.join(os.getcwd(), 'emotion_data.db')
        self.running = True
        self.init_database()
        
        # Set signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print(f"✅ {model_name} analyzer initialized")
        print(f"📷 Camera index: {self.camera_index}")
        print(f"🔧 Camera backend: {self.camera_backend}")
        print(f"🗄️ Database: {self.db_path}")
    
    def signal_handler(self, signum, frame):
        """Signal handler for graceful shutdown"""
        print(f"\n🛑 Received exit signal {signum}, stopping...")
        self.running = False
    
    def init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emotion_records'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check if emotion_level column exists
            cursor.execute("PRAGMA table_info(emotion_records)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'emotion_level' not in columns:
                print("🔄 Detected old database, adding emotion_level column...")
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN emotion_level REAL DEFAULT 0.0')
                print("✅ emotion_level column added")
            
            # Check screen content-related columns
            if 'app_name' not in columns:
                print("🔄 Detected old database, adding screen content columns...")
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN app_name TEXT DEFAULT "Unknown App"')
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN app_category TEXT DEFAULT "Other"')
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN content_description TEXT DEFAULT "Unrecognized app/content"')
                cursor.execute('ALTER TABLE emotion_records ADD COLUMN screen_path TEXT')
                print("✅ Screen content columns added")
        else:
            # Create table with all columns
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
                    app_name TEXT DEFAULT "Unknown App",
                    app_category TEXT DEFAULT "Other",
                    content_description TEXT DEFAULT "Unrecognized app/content",
                    screen_path TEXT
                )
            ''')
        conn.commit()
        conn.close()
    
    def save_image(self, image, timestamp, image_index=None):
        """Save image locally, directory: year/month/day/hour/"""
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        # Get parent of current directory
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
        
        # Append index to filename if provided
        if image_index is not None:
            filename = f'{timestamp}_{image_index:02d}.jpg'
        else:
            filename = f'{timestamp}.jpg'
            
        image_path = os.path.join(dir_path, filename)
        cv2.imwrite(image_path, image)
        return image_path
    
    def image_to_base64(self, image):
        """Convert OpenCV image to base64 string"""
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Encode to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return img_str
    
    def capture_screen(self, timestamp):
        """Capture screen screenshot"""
        try:
            import pyautogui
            print(f"🖥️ Capturing screen...")
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            
            # Convert to OpenCV
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Save screenshot
            saved_screen_path = self.save_screen(screenshot_cv, timestamp)
            
            print(f"✅ Screen saved to: {saved_screen_path}")
            return screenshot_cv, saved_screen_path
            
        except ImportError:
            print("❌ pyautogui not installed, cannot capture screen")
            return None, None
        except Exception as e:
            print(f"❌ Failed to capture screen: {e}")
            return None, None
    
    def save_screen(self, screen_image, timestamp):
        """Save screen to local path, aligned with video path"""
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        # Get parent of current dir
        parent_dir = os.path.dirname(os.path.abspath('.'))
        dir_path = os.path.join(
            parent_dir,
            'testvideos',  # Store with videos
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
        """Analyze emotion - subclasses must implement, receive list of images"""
        raise NotImplementedError("Subclasses must implement analyze_emotion method")
    
    def _get_default_result(self):
        """Get default result"""
        return {
            "has_face": False,
            "emotion": "None",
            "confidence": 0.0,
            "emotion_level": 0.0
        }
    
    def _get_default_screen_result(self):
        """Get default screen analysis result"""
        return {
            "app_name": "Unknown App",
            "app_category": "Other",
            "content_description": "Unrecognized app/content"
        }
    
    def save_to_database(self, timestamp, emotion, confidence, has_face, image_path=None, emotion_level=0.0, 
                        app_name="未知应用", app_category="其他", content_description="无法识别当前应用和内容", screen_path=None):
        """Save analysis result to database, including screen content fields"""
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
        """Record video from camera for the specified duration"""
        import cv2
        import tempfile
        import os
        
        print(f"🎬 Start recording {duration} seconds of video...")
        
        # Open camera
        cap = cv2.VideoCapture(self.camera_index, self.camera_backend)
        if not cap.isOpened():
            raise Exception(f"Cannot open camera {self.camera_index}")
        
        # Get camera params
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30  # default FPS
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create temp video file
        temp_video_path = tempfile.mktemp(suffix='.mp4')
        
        # Setup video encoder
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            cap.release()
            raise Exception("Cannot create video file")
        
        # Calculate frames to record
        total_frames = int(fps * duration)
        frame_count = 0
        
        try:
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    print(f"⚠️ 第 {frame_count + 1} 帧读取失败")
                    break
                
                # Write frame
                out.write(frame)
                frame_count += 1
                
                # Show progress
                if frame_count % fps == 0:
                    elapsed_time = frame_count / fps
                    print(f"   📹 Recorded {elapsed_time:.1f}/{duration} seconds")
        
        finally:
            # Release resources
            cap.release()
            out.release()
        
        print(f"✅ Video recorded: {frame_count} frames, {frame_count/fps:.2f} seconds")
        return temp_video_path
    
    def video_to_base64(self, video_path):
        """Convert video file to base64 string"""
        import base64
        
        try:
            with open(video_path, 'rb') as video_file:
                video_data = video_file.read()
                video_base64 = base64.b64encode(video_data).decode('utf-8')
                return video_base64
        except Exception as e:
            raise Exception(f"Failed to read video file: {e}")
    
    def extract_frames_from_video(self, video_path, num_frames=6):
        """Extract specified number of frames from video"""
        import cv2
        
        print(f"🎬 Extracting {num_frames} frames from video...")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Cannot open video file")
        
        # Get video metadata
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps
        
        print(f"📊 Video info: {total_frames} frames, {fps:.1f} fps, {duration:.2f} seconds")
        
        # Compute frame step
        if total_frames <= num_frames:
            # If few frames, extract all
            frame_indices = list(range(total_frames))
        else:
            # Uniformly sample frames
            step = total_frames / num_frames
            frame_indices = [int(i * step) for i in range(num_frames)]
        
        frames = []
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
                print(f"   ✅ Extracted {i+1}/{num_frames} frame (original frame {frame_idx})")
            else:
                print(f"   ❌ Failed to extract frame {i+1}/{num_frames}")
        
        cap.release()
        
        if not frames:
            raise Exception("No frames extracted from video")
        
        print(f"✅ Successfully extracted {len(frames)} frames")
        return frames
    
    def analyze_video_emotion(self, video_path):
        """Analyze emotions in video - extract 6 frames and send to model"""
        try:
            print(f"🎬 Extracting 6 frames from video...")
            
            # 从视频中提取6帧
            frames = self.extract_frames_from_video(video_path, num_frames=6)
            
            print(f"📊 Successfully extracted {len(frames)} frames")
            
            # 将帧图像传给模型进行分析
            analysis_results = self.analyze_emotion(frames)
            
            print(f"📊 Model returned {len(analysis_results)} results")
            for i, result in enumerate(analysis_results):
                print(f"   ✅ Result {i+1}: {result['emotion']} (level: {result['emotion_level']:.2f})")
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ Video analysis failed: {e}")
            return [self._get_default_result() for _ in range(6)]
    
    def _calculate_average_result(self, results):
        """Compute average of multiple analysis results"""
        if not results:
            return self._get_default_result()
        
        # Count emotion types
        emotion_counts = {}
        total_confidence = 0
        total_emotion_level = 0
        total_has_face = 0
        
        for result in results:
            emotion = result.get('emotion', 'None')
            confidence = result.get('confidence', 0.0)
            emotion_level = result.get('emotion_level', 0.0)
            has_face = result.get('has_face', False)
            
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            total_confidence += confidence
            total_emotion_level += emotion_level
            if has_face:
                total_has_face += 1
        
        # Choose most frequent emotion
        if emotion_counts:
            most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])
            dominant_emotion = most_common_emotion[0]
        else:
            dominant_emotion = 'None'
        
        # Compute averages
        avg_confidence = total_confidence / len(results)
        avg_emotion_level = total_emotion_level / len(results)
        avg_has_face = total_has_face / len(results) > 0.5  # more than half frames have faces
        
        return {
            "has_face": avg_has_face,
            "emotion": dominant_emotion,
            "confidence": avg_confidence,
            "emotion_level": avg_emotion_level
        }
    
    def process_video_capture(self):
        """Full video capture and analysis pipeline"""
        try:
            # Record overall start time
            total_start_time = time.time()
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # Record video
            print(f"[{timestamp}] Recording video...")
            capture_start = time.time()
            video_path = self.capture_video(duration=3.0)
            capture_time = time.time() - capture_start
            print(f"[{timestamp}] Video recording done - elapsed: {capture_time:.2f}s")
            
            # Capture screen
            print(f"[{timestamp}] Capturing screen...")
            screen_start = time.time()
            screen_image, screen_path = self.capture_screen(timestamp)
            screen_time = time.time() - screen_start
            print(f"[{timestamp}] Screen capture done - elapsed: {screen_time:.2f}s")
            
            # Analyze video emotion
            print(f"[{timestamp}] Analyzing video emotion...")
            analysis_start = time.time()
            analysis_results = self.analyze_video_emotion(video_path)
            analysis_time = time.time() - analysis_start
            print(f"[{timestamp}] Video emotion analysis done - elapsed: {analysis_time:.2f}s")
            
            # Analyze screen content (if supported)
            screen_analysis_result = None
            if screen_image is not None and hasattr(self, 'analyze_screen_content'):
                print(f"[{timestamp}] Analyzing screen content...")
                screen_analysis_start = time.time()
                try:
                    screen_analysis_result = self.analyze_screen_content(screen_image)
                    screen_analysis_time = time.time() - screen_analysis_start
                    print(f"[{timestamp}] Screen content analysis done - elapsed: {screen_analysis_time:.2f}s")
                except Exception as e:
                    print(f"[{timestamp}] Screen content analysis failed: {e}")
                    screen_analysis_result = self._get_default_screen_result()
            else:
                screen_analysis_result = self._get_default_screen_result()
            
            # Save video file
            print(f"[{timestamp}] Saving video...")
            save_start = time.time()
            saved_video_path = self.save_video(video_path, timestamp)
            save_time = time.time() - save_start
            print(f"[{timestamp}] Video saved to: {saved_video_path} - elapsed: {save_time:.2f}s")
            
            # Save to database - handle 6 analysis results
            db_start = time.time()
            saved_results = []
            
            for i, analysis_result in enumerate(analysis_results):
                # Generate unique timestamp for each result
                result_timestamp = f"{timestamp}_{i:02d}"
                
                # Save to DB including screen content
                self.save_to_database(
                    timestamp=result_timestamp,
                    emotion=analysis_result['emotion'],
                    confidence=analysis_result['confidence'],
                    has_face=analysis_result['has_face'],
                    image_path=saved_video_path,  # use video path instead of image path
                    emotion_level=analysis_result['emotion_level'],
                    app_name=screen_analysis_result.get('app_name', 'Unknown App'),
                    app_category=screen_analysis_result.get('app_category', 'Other'),
                    content_description=screen_analysis_result.get('content_description', 'Unrecognized app/content'),
                    screen_path=screen_path
                )
                
                saved_results.append({
                    'timestamp': result_timestamp,
                    'result': analysis_result,
                    'screen_analysis': screen_analysis_result
                })
                
                # Print each result detail
                emotion_info = f"情绪={analysis_result['emotion']}"
                if analysis_result['has_face'] and analysis_result['emotion'] != 'None':
                    emotion_info += f", level={analysis_result['emotion_level']:.2f}"
                print(f"[{timestamp}] Result {i+1}/6: face={analysis_result['has_face']}, {emotion_info}, confidence={analysis_result['confidence']:.2f}")
            
            # Print screen analysis result
            if screen_analysis_result:
                print(f"[{timestamp}] Screen: app={screen_analysis_result.get('app_name', 'Unknown')}, "
                      f"category={screen_analysis_result.get('app_category', 'Other')}, "
                      f"desc={screen_analysis_result.get('content_description', 'No description')}")
            
            db_time = time.time() - db_start
            print(f"[{timestamp}] Data saved - elapsed: {db_time:.2f}s")
            
            # Compute total time
            total_time = time.time() - total_start_time
            
            print(f"[{timestamp}] Video and screen analysis finished!")
            print(f"[{timestamp}] Total processing time: {total_time:.2f}s")
            print(f"[{timestamp}] Optimization: analyze video before saving to avoid re-read")
            print(f"[{timestamp}] Extract 6 frames and return 6 analysis results")
            print(f"[{timestamp}] Analyze screen content and save with the same record")
            
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
            print(f"[{datetime.now().strftime('%Y%m%d-%H%M%S')}] Error during video processing: {e}")
            return None
    
    def save_video(self, video_path, timestamp):
        """Save video locally, directory: year/month/day/hour/"""
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        # Get parent of current dir
        parent_dir = os.path.dirname(os.path.abspath('.'))
        dir_path = os.path.join(
            parent_dir,
            'testvideos',  # store under testvideos
            dt.strftime('%Y'),
            dt.strftime('%m'),
            dt.strftime('%d'),
            dt.strftime('%H')
        )
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        filename = f'{timestamp}_video.mp4'
        saved_video_path = os.path.join(dir_path, filename)
        
        # Copy video file
        import shutil
        shutil.copy2(video_path, saved_video_path)
        return saved_video_path

    def run_continuous_video(self, interval_minutes=1.0):
        """Continuous mode - video recognition"""
        print("🚀 Emotion analysis system started - video recognition mode")
        print(f"🤖 Model: {self.model_name}")
        print(f"📷 Camera index: {self.camera_index}")
        print(f"⏰ Interval: {interval_minutes} minutes")
        print(f"🎬 Each capture: 3s video")
        print("🛑 Press Ctrl+C to stop")
        print("="*60)
        
        interval_seconds = int(interval_minutes * 60)  # convert to seconds
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n🔄 Loop {cycle_count} - {current_time}")
                print("-" * 40)
                
                # Execute capture and analysis
                result = self.process_video_capture()
                
                if result:
                    print(f"✅ Loop {cycle_count} completed")
                else:
                    print(f"❌ Loop {cycle_count} failed")
                
                # Wait before next loop
                if self.running:
                    print(f"⏳ Waiting {interval_minutes} minutes before next capture...")
                    print(f"🕐 Next Turn: {datetime.fromtimestamp(time.time() + interval_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Segment wait, check every second for exit
                    for i in range(interval_seconds):
                        if not self.running:
                            break
                        time.sleep(1)
                        
                        # Show countdown every 5 seconds
                        if (i + 1) % 5 == 0:
                            remaining = interval_seconds - (i + 1)
                            print(f"⏰ Remaining: {remaining} seconds")
                
            except KeyboardInterrupt:
                print("\n🛑 Interrupted by user")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error during loop: {e}")
                print("🔄 Retry in 5 seconds...")
                time.sleep(5)
        
        print("\n👋 Stopped")
        print(f"📊 Completed {cycle_count} analysis loops")

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
    """Simplified: return default internal camera (index 0)"""
    return [{
        'index': 0,
        'backend': cv2.CAP_ANY,
        'backend_name': 'Auto',
        'resolution': 'Auto',
        'fps': 30.0,
        'is_external': False,
        'display_name': 'Default internal camera'
    }]

def select_camera():
    """Simplified: return default internal camera (index 0)"""
    return {
        'index': 0,
        'backend': cv2.CAP_ANY,
        'backend_name': 'Auto',
        'resolution': 'Auto',
        'fps': 30.0,
        'is_external': False,
        'display_name': 'Default internal camera'
    }