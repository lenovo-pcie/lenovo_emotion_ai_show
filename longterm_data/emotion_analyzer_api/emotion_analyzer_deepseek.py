import cv2
import requests
import json
import time
import base64
import io
from PIL import Image
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerDeepSeek(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=None, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "DeepSeek")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        # 加载标准分类提示词
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """分析屏幕截图内容，识别使用的APP和内容分类"""
        prompt = (
            "Analyze this screen screenshot and identify the following information. "
            "Return ONLY a JSON object in the following format:\n"
            "{"
            "\"app_name\": \"Application Name\", "
            "\"app_category\": \"Category\", "
            "\"content_description\": \"10-15字描述\""
            "}\n"
            f"{self.screen_class_prompt}\n"
            "Content description requirements:\n"
            "- Around 50 characters, provide more detailed content description\n"
            "- Describe the current activity being performed\n"
            "- Include specific operations or content\n"
            "- If there are people in the image, list their names\n"
            "- If watching a video, describe the video content (including title, topic, people, etc.)\n"
            "- If it's a chat app, describe the chat partner and content topic\n"
            "Example for chat:\n"
            "{\"app_name\": \"WeChat\", \"app_category\": \"Social\", \"content_description\": \"与张三聊天讨论会议\"}\n"
            "Example for video:\n"
            "{\"app_name\": \"Bilibili\", \"app_category\": \"Entertainment\", \"content_description\": \"观看Python教程，讲师李四\"}\n"
            "If unable to identify the application, return:\n"
            "{"
            "\"app_name\": \"Unknown App\", "
            "\"app_category\": \"Other\", "
            "\"content_description\": \"Unable to identify current app and content\""
            "}\n"
            "DO NOT output any explanation or extra text, ONLY the JSON object."
        )
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            # 准备图片的base64数据
            image_base64 = self.image_to_base64(screen_image)
            image_url = f"data:image/jpeg;base64,{image_base64}"
            
            request_data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1024,
                "temperature": 0.1
            }
            
            start_time = time.time()
            print(f"🖥️ 正在调用DeepSeek API分析屏幕内容...")
            
            response = requests.post(self.base_url, headers=headers, json=request_data, timeout=30)
            end_time = time.time()
            api_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
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
        """使用DeepSeek API分析多张图像中的情绪"""
        prompt = (
            "Analyze the emotion of the person in this image. "
            "Return ONLY a JSON object in the following format:\n"
            "{"
            "\"has_face\": true/false, "
            "\"emotion\": \"Neutral/Happy/Angry/Sad/Surprised/Worried/None\", "
            "\"confidence\": 0.0-1.0, "
            "\"emotion_level\": 0.0-1.0"
            "}\n"
            "emotion_level indicates the intensity of the emotion:\n"
            "- 0.0: No emotion or very slight\n"
            "- 0.3: Slight emotion\n"
            "- 0.5: Moderate emotion\n"
            "- 0.7: Strong emotion\n"
            "- 1.0: Extreme emotion\n"
            "If no face is detected, set has_face to false, emotion to None, confidence to 0.0, emotion_level to 0.0. "
            "DO NOT output any explanation or extra text, ONLY the JSON object."
        )
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        results = []
        start_time = time.time()
        
        try:
            print(f"🌐 正在调用DeepSeek API分析 {len(images)} 张图片...")
            
            for i, image in enumerate(images):
                # 准备单张图片的base64数据
                image_base64 = self.image_to_base64(image)
                image_url = f"data:image/jpeg;base64,{image_base64}"
                
                request_data = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.1
                }
                
                # 调试：打印请求数据的前100个字符
                request_str = json.dumps(request_data, ensure_ascii=False)
                print(f"🔍 请求数据预览 (图片 {i+1}): {request_str[:100]}...")
                
                response = requests.post(self.base_url, headers=headers, json=request_data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        response_text = result['choices'][0]['message']['content']
                        import re
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            try:
                                result_data = json.loads(json_str)
                                results.append(result_data)
                                print(f"✅ 图片 {i+1}/{len(images)} 分析成功")
                            except json.JSONDecodeError:
                                print(f"❌ 图片 {i+1}/{len(images)} JSON解析失败: {json_str}")
                                results.append(self._get_default_result())
                        else:
                            print(f"❌ 图片 {i+1}/{len(images)} 未找到JSON格式响应: {response_text}")
                            results.append(self._get_default_result())
                    else:
                        print(f"❌ 图片 {i+1}/{len(images)} API响应格式异常")
                        results.append(self._get_default_result())
                else:
                    print(f"❌ 图片 {i+1}/{len(images)} API请求失败，状态码: {response.status_code}")
                    print(f"❌ 错误信息: {response.text}")
                    results.append(self._get_default_result())
            
            end_time = time.time()
            api_time = end_time - start_time
            print(f"✅ 所有图片分析完成 - 总耗时: {api_time:.2f}秒")
            return results
            
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