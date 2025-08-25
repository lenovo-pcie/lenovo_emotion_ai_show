import cv2
import requests
import json
import time
import base64
import io
from PIL import Image
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerQwen(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=None, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "Qwen")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        # 加载标准分类提示词
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """分析屏幕截图内容，识别使用的APP和内容分类"""
        prompt = f"""分析这张屏幕截图，识别以下信息并严格按照JSON格式返回：
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
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 准备图片的base64数据
        image_base64 = self.image_to_base64(screen_image)
        image_url = f"data:image/jpeg;base64,{image_base64}"
        
        request_data = {
            "model": "qwen-vl-max-latest",
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "请分析这张屏幕截图中的内容。"}
                    ]
                }
            ],
            "temperature": 0.1
        }
        
        start_time = time.time()
        try:
            print(f"🖥️ 正在调用Qwen API分析屏幕内容...")
            response = requests.post(self.base_url, headers=headers, json=request_data, timeout=30)
            end_time = time.time()
            api_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
                    # Qwen返回的content可能是字符串或列表
                    if isinstance(response_text, list):
                        response_text = ''.join([x.get('text', '') for x in response_text if isinstance(x, dict)])
                    
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
    
    def analyze_emotion(self, images):
        """使用Qwen API分析多张图像中的情绪"""
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
        - 其他情绪：中立、愤怒、悲伤、惊讶、担忧
        
        情绪分类说明：
        - 中立：平静、无特殊表情
        - 快乐：微笑、开心、愉悦（优先识别，即使轻微也要识别为快乐）
        - 愤怒：皱眉、生气、不满
        - 悲伤：难过、沮丧、忧郁
        - 惊讶：震惊、意外、吃惊
        - 担忧：焦虑、担心、不安
        
        情绪级别说明（emotion_level）：
        - 0.0：无情绪或情绪极轻微
        - 0.3：轻微情绪（对于快乐情绪，即使是很轻微的微笑也要给予0.3以上的强度）
        - 0.5：中等情绪
        - 0.7：较强情绪
        - 1.0：极度强烈情绪
        
        特别注意：优先识别快乐情绪，即使置信度较低也要识别为快乐。
        
        如果没有检测到人脸，请返回：
        {
            "has_face": false,
            "emotion": "无",
            "confidence": 0.0,
            "emotion_level": 0.0
        }
        
        请确保返回的是有效的JSON数组格式，数组长度应该等于图片数量。
        """
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 准备所有图片的base64数据
        image_contents = []
        for image in images:
            image_base64 = self.image_to_base64(image)
            image_url = f"data:image/jpeg;base64,{image_base64}"
            image_contents.append({"type": "image_url", "image_url": {"url": image_url}})
        
        request_data = {
            "model": "qwen-vl-max-latest",
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                },
                {
                    "role": "user",
                    "content": image_contents + [
                        {"type": "text", "text": "请分析这些图片中的情绪。"}
                    ]
                }
            ],
            "temperature": 0.1  # 降低temperature提高一致性
        }
        
        start_time = time.time()
        try:
            print(f"🌐 正在调用Qwen API分析 {len(images)} 张图片...")
            response = requests.post(self.base_url, headers=headers, json=request_data, timeout=60)
            end_time = time.time()
            api_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
                    # Qwen返回的content可能是字符串或列表
                    if isinstance(response_text, list):
                        response_text = ''.join([x.get('text', '') for x in response_text if isinstance(x, dict)])
                    import re
                    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        try:
                            result_data = json.loads(json_str)
                            
                            # 后处理：只增强快乐情绪的识别
                            for item in result_data:
                                if item.get("emotion") == "快乐":
                                    if item.get("confidence", 0) < 0.3:
                                        item["confidence"] = 0.3
                                    if item.get("emotion_level", 0) < 0.3:
                                        item["emotion_level"] = 0.3
                            
                            print(f"✅ API调用成功 - 耗时: {api_time:.2f}秒")
                            return result_data
                        except json.JSONDecodeError:
                            print(f"❌ JSON解析失败: {json_str}")
                            print(f"⚠️ API调用耗时: {api_time:.2f}秒")
                            return [self._get_default_result() for _ in images]
                    else:
                        print(f"❌ 未找到JSON格式响应: {response_text}")
                        print(f"⚠️ API调用耗时: {api_time:.2f}秒")
                        return [self._get_default_result() for _ in images]
                else:
                    print("❌ API响应格式异常")
                    print(f"⚠️ API调用耗时: {api_time:.2f}秒")
                    return [self._get_default_result() for _ in images]
            else:
                print(f"❌ API请求失败，状态码: {response.status_code}")
                print(f"❌ 错误信息: {response.text}")
                print(f"⚠️ API调用耗时: {api_time:.2f}秒")
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