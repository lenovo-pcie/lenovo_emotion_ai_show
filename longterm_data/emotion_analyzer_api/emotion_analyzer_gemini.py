import cv2
import requests
import json
import time
import base64
import io
from PIL import Image
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerGemini(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=None, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "Gemini")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent"
        # 加载标准分类提示词
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """分析屏幕截图内容，识别使用的APP和内容分类"""
        # 构建屏幕内容分析提示词
        prompt = f"""
        请分析这张屏幕截图，识别以下信息并严格按照JSON格式返回：
        {{
            "app_name": "应用名称",
            "app_category": "应用分类",
            "content_description": "10-15字描述"
        }}
        
        {self.screen_class_prompt}
        
        详细描述要求：
        - 10-15字，简洁描述当前活动
        - 如果图中有人物，请列出人物名字
        - 如果是在看视频，请说明视频标题和主要人物
        - 如果是聊天应用，请说明聊天对象和主题
        - 如果是工作文档，请说明文档类型和主题
        
        示例返回：
        {{
            "app_name": "微信",
            "app_category": "社交",
            "content_description": "与张三聊天讨论会议"
        }}
        
        视频观看示例：
        {{
            "app_name": "哔哩哔哩",
            "app_category": "娱乐",
            "content_description": "观看Python教程，讲师李四"
        }}
        
        如果无法识别应用，请返回：
        {{
            "app_name": "未知应用",
            "app_category": "其他",
            "content_description": "无法识别当前应用和内容"
        }}
        """
        
        # 构建请求数据
        request_data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 1024
            }
        }
        
        # 转换图像格式
        if isinstance(screen_image, str):
            # 如果是文件路径，读取图像
            image = cv2.imread(screen_image)
            if image is None:
                print(f"❌ 无法读取屏幕截图: {screen_image}")
                return self._get_default_screen_result()
        else:
            # 如果是numpy数组
            image = screen_image
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # 将图像转换为base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 添加图片到请求
        request_data["contents"][0]["parts"].append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_base64
            }
        })
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 发送HTTP请求
            url = f"{self.base_url}?key={self.api_key}"
            print(f"🖥️ 正在调用Gemini API分析屏幕内容...")
            response = requests.post(url, headers=headers, json=request_data, timeout=30)
            
            # 计算耗时
            end_time = time.time()
            api_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取响应文本
                if 'candidates' in result and len(result['candidates']) > 0:
                    response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    # 提取JSON部分
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        try:
                            result_data = json.loads(json_str)
                            print(f"✅ 屏幕内容分析成功 - 耗时: {api_time:.2f}秒")
                            print(f"   📱 应用: {result_data.get('app_name', '未知')}")
                            print(f"   📂 分类: {result_data.get('app_category', '其他')}")
                            print(f"   📝 描述: {result_data.get('content_description', '无描述')}")
                            return result_data
                        except json.JSONDecodeError:
                            print(f"❌ 屏幕内容分析JSON解析失败: {json_str}")
                            print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                            return self._get_default_screen_result()
                    else:
                        print(f"❌ 屏幕内容分析未找到JSON格式响应: {response_text}")
                        print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                        return self._get_default_screen_result()
                else:
                    print("❌ 屏幕内容分析API响应格式异常")
                    print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                    return self._get_default_screen_result()
            else:
                print(f"❌ 屏幕内容分析API请求失败，状态码: {response.status_code}")
                print(f"❌ 错误信息: {response.text}")
                print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                return self._get_default_screen_result()
                
        except requests.exceptions.Timeout:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"⏰ 屏幕内容分析API请求超时 - 耗时: {api_time:.2f}秒")
            return self._get_default_screen_result()
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"❌ 屏幕内容分析API请求异常: {e} - 耗时: {api_time:.2f}秒")
            return self._get_default_screen_result()
        except Exception as e:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"❌ 屏幕内容分析过程中出现错误: {e} - 耗时: {api_time:.2f}秒")
            return self._get_default_screen_result()
    
    def _get_default_screen_result(self):
        """获取默认的屏幕分析结果"""
        return {
            "app_name": "未知应用",
            "app_category": "其他",
            "content_description": "无法识别当前应用和内容"
        }
    
    def analyze_emotion(self, images):
        """使用Gemini HTTP API分析多张图像中的情绪"""
        # 构建提示词
        prompt = """
        请分析这6张图片中人物的情绪状态，特别注意快乐情绪的识别。请严格按照以下格式返回JSON数组：
        [
            {
                "has_face": true/false,
                "emotion": "中立/快乐/愤怒/悲伤/惊讶/担忧",
                "confidence": 0.0-1.0,
                "emotion_level": 0.0-1.0
            },
            {
                "has_face": true/false,
                "emotion": "中立/快乐/愤怒/悲伤/惊讶/担忧", 
                "confidence": 0.0-1.0,
                "emotion_level": 0.0-1.0
            },
            ...
        ]
        
        情绪识别规则：
        - 快乐情绪：只要看到微笑、嘴角上扬、眼睛微眯、面部表情轻松愉快等任何快乐迹象，即使程度轻微也要识别为"快乐"
        - 快乐情绪识别要更加敏感，不要过于保守
        - 担忧情绪：只有在非常明显的焦虑、担心、不安表情时才识别为"担忧"，轻微的不确定表情应识别为"中立"
        - 担忧情绪识别要更加保守，避免过度敏感
        - 其他情绪：中立、愤怒、悲伤、惊讶
        
        情绪分类说明：
        - 中立：平静、无特殊表情，包括轻微的不确定表情
        - 快乐：微笑、开心、愉悦（优先识别，即使轻微也要识别为快乐）
        - 愤怒：皱眉、生气、不满
        - 悲伤：难过、沮丧、忧郁
        - 惊讶：震惊、意外、吃惊
        - 担忧：明显的焦虑、担心、不安（只有在非常明显时才识别）
        
        情绪级别说明（emotion_level）：
        - 0.0：无情绪或情绪极轻微
        - 0.3：轻微情绪（对于快乐情绪，即使是很轻微的微笑也要给予0.3以上的强度）
        - 0.5：中等情绪
        - 0.7：较强情绪
        - 1.0：极度强烈情绪
        
        特别注意：
        - 优先识别快乐情绪，即使置信度较低也要识别为快乐
        - 担忧情绪识别要更加保守，只有在非常明显时才识别，轻微的不确定表情应归类为"中立"
        
        如果没有检测到人脸，请返回：
        {
            "has_face": false,
            "emotion": "无",
            "confidence": 0.0,
            "emotion_level": 0.0
        }
        
        请确保返回的是有效的JSON数组格式，数组长度应该等于图片数量。
        """
        
        # 构建请求数据
        request_data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048
            }
        }
        
        # 添加所有图片到请求中
        for i, image in enumerate(images):
            # 转换图像格式
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            
            # 将图像转换为base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # 添加图片到请求
            request_data["contents"][0]["parts"].append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }
            })
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 发送HTTP请求
            url = f"{self.base_url}?key={self.api_key}"
            print(f"🌐 正在调用Gemini API分析 {len(images)} 张图片...")
            response = requests.post(url, headers=headers, json=request_data, timeout=30)
            
            # 计算耗时
            end_time = time.time()
            api_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取响应文本
                if 'candidates' in result and len(result['candidates']) > 0:
                    response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    # 提取JSON部分
                    import re
                    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        try:
                            result_data = json.loads(json_str)
                            
                            # 后处理：增强快乐情绪识别，降低担忧情绪敏感度
                            for item in result_data:
                                if item.get("emotion") == "快乐":
                                    if item.get("confidence", 0) < 0.3:
                                        item["confidence"] = 0.3
                                    if item.get("emotion_level", 0) < 0.3:
                                        item["emotion_level"] = 0.3
                                elif item.get("emotion") == "担忧":
                                    # 降低担忧情绪的敏感度
                                    confidence = item.get("confidence", 0)
                                    emotion_level = item.get("emotion_level", 0)
                                    
                                    # 如果置信度或情绪强度较低，将担忧改为中立
                                    if confidence < 0.6 or emotion_level < 0.5:
                                        item["emotion"] = "中立"
                                        item["confidence"] = max(confidence * 0.8, 0.3)
                                        item["emotion_level"] = max(emotion_level * 0.8, 0.2)
                                    else:
                                        # 即使识别为担忧，也降低其强度
                                        item["confidence"] = confidence * 0.9
                                        item["emotion_level"] = emotion_level * 0.9
                            
                            print(f"✅ API调用成功 - 耗时: {api_time:.2f}秒")
                            return result_data
                        except json.JSONDecodeError:
                            print(f"❌ JSON解析失败: {json_str}")
                            print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                            return [self._get_default_result() for _ in images]
                    else:
                        print(f"❌ 未找到JSON格式响应: {response_text}")
                        print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                        return [self._get_default_result() for _ in images]
                else:
                    print("❌ API响应格式异常")
                    print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                    return [self._get_default_result() for _ in images]
            else:
                print(f"❌ API请求失败，状态码: {response.status_code}")
                print(f"❌ 错误信息: {response.text}")
                print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                return [self._get_default_result() for _ in images]
                
        except requests.exceptions.Timeout:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"⏰ API请求超时 - 耗时: {api_time:.2f}秒")
            return [self._get_default_result() for _ in images]
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"❌ API请求异常: {e} - 耗时: {api_time:.2f}秒")
            return [self._get_default_result() for _ in images]
        except Exception as e:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"❌ 分析过程中出现错误: {e} - 耗时: {api_time:.2f}秒")
            return [self._get_default_result() for _ in images] 