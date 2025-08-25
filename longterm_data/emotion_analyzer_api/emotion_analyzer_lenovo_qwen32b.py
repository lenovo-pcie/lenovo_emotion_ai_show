import cv2
import requests
import json
import time
import base64
import io
from PIL import Image
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerLenovoQwen32b(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=0, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "Lenovo-Qwen32b")
        # Remote Ollama service config
        self.base_url = "http://211.93.18.61:33434"
        self.model_name = "qwen2.5vl:32b"  # qwen2.5vl:32b supports image analysis
        self.api_key = "LNV-666d8c88c76a00ed2c2f3128bcbb20f4"  # API key
        # Load standard screen classification prompt
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """Analyze screen content and classify app and content"""
        prompt = (
            "分析这个屏幕截图并识别以下信息。"
            "只返回JSON格式的对象：\n"
            "{"
            "\"app_name\": \"应用名称\", "
            "\"app_category\": \"应用分类\", "
            "\"content_description\": \"10-15字描述\""
            "}\n"
            f"{self.screen_class_prompt}\n"
            "内容描述要求：\n"
            "- 10-15字，简洁描述当前活动\n"
            "- 如果图片中有人员，列出姓名\n"
            "- 如果观看视频，说明视频标题和主要人物\n"
            "- 如果是聊天应用，说明聊天对象和主题\n"
            "聊天示例：\n"
            "{\"app_name\": \"微信\", \"app_category\": \"社交\", \"content_description\": \"与张三聊天讨论会议\"}\n"
            "视频示例：\n"
            "{\"app_name\": \"哔哩哔哩\", \"app_category\": \"娱乐\", \"content_description\": \"观看Python教程，讲师李四\"}\n"
            "如果无法识别应用，返回：\n"
            "{"
            "\"app_name\": \"未知应用\", "
            "\"app_category\": \"其他\", "
            "\"content_description\": \"无法识别当前应用和内容\""
            "}\n"
            "不要输出任何解释或额外文本，只返回JSON对象。"
        )
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            # 准备图片的base64数据
            image_base64 = self.image_to_base64(screen_image)
            
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            }
            
            start_time = time.time()
            print(f"🖥️ Calling remote Ollama API to analyze screen content...")
            
            response = requests.post(f"{self.base_url}/api/generate", headers=headers, json=request_data, timeout=30)
            end_time = time.time()
            api_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'response' in result:
                    response_text = result['response']
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        try:
                            result_data = json.loads(json_str)
                            print(f"✅ Screen content analyzed - elapsed: {api_time:.2f}s")
                            print(f"   📱 App: {result_data.get('app_name', 'Unknown')}")
                            print(f"   📂 Category: {result_data.get('app_category', 'Other')}")
                            print(f"   📝 Description: {result_data.get('content_description', 'No description')}")
                            return result_data
                        except json.JSONDecodeError:
                            print(f"❌ Screen content JSON parse failed: {json_str}")
                            print(f"⚠️  API call elapsed: {api_time:.2f}s")
                            return self._get_default_screen_result()
                    else:
                        print(f"❌ Screen content analysis did not return JSON: {response_text}")
                        print(f"⚠️  API call elapsed: {api_time:.2f}s")
                        return self._get_default_screen_result()
                else:
                    print("❌ Screen content API response format error")
                    print(f"⚠️  API call elapsed: {api_time:.2f}s")
                    return self._get_default_screen_result()
            else:
                print(f"❌ Screen content API request failed, status: {response.status_code}")
                print(f"❌ Error: {response.text}")
                print(f"⚠️  API call elapsed: {api_time:.2f}s")
                return self._get_default_screen_result()
                
        except requests.exceptions.Timeout:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"⏰ Screen content API request timeout - elapsed: {api_time:.2f}s")
            return self._get_default_screen_result()
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"❌ Screen content API request error: {e} - elapsed: {api_time:.2f}s")
            return self._get_default_screen_result()
        except Exception as e:
            end_time = time.time()
            api_time = end_time - start_time
            print(f"❌ Screen content analysis error: {e} - elapsed: {api_time:.2f}s")
            return self._get_default_screen_result()
    
    def analyze_emotion(self, images):
        """Analyze emotions for multiple images using remote Ollama API"""
        prompt = (
            "分析这张图片中人物的情绪。"
            "只返回JSON格式的对象：\n"
            "{"
            "\"has_face\": true/false, "
            "\"emotion\": \"中立/快乐/愤怒/悲伤/惊讶/担忧/无\", "
            "\"confidence\": 0.0-1.0, "
            "\"emotion_level\": 0.0-1.0"
            "}\n"
            "emotion_level表示情绪强度：\n"
            "- 0.0：无情绪或非常轻微\n"
            "- 0.3：轻微情绪\n"
            "- 0.5：中等情绪\n"
            "- 0.7：强烈情绪\n"
            "- 1.0：极端情绪\n"
            "如果未检测到人脸，设置has_face为false，emotion为无，confidence为0.0，emotion_level为0.0。"
            "不要输出任何解释或额外文本，只返回JSON对象。"
        )
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        results = []
        start_time = time.time()
        
        try:
            print(f"🌐 Calling remote Ollama API to analyze {len(images)} images...")
            
            for i, image in enumerate(images):
                # Prepare base64 image
                image_base64 = self.image_to_base64(image)
                
                request_data = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 1024
                    }
                }
                
                # Debug: preview first 100 chars of request
                request_str = json.dumps(request_data, ensure_ascii=False)
                #print(f"🔍 请求数据预览 (图片 {i+1}): {request_str[:100]}...")
                
                response = requests.post(f"{self.base_url}/api/generate", headers=headers, json=request_data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'response' in result:
                        response_text = result['response']
                        import re
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            try:
                                result_data = json.loads(json_str)
                                results.append(result_data)
                                print(f"✅ Image {i+1}/{len(images)} analyzed successfully")
                            except json.JSONDecodeError:
                                print(f"❌ Image {i+1}/{len(images)} JSON parse failed: {json_str}")
                                results.append(self._get_default_result())
                        else:
                            print(f"❌ Image {i+1}/{len(images)} did not return JSON: {response_text}")
                            results.append(self._get_default_result())
                    else:
                        print(f"❌ Image {i+1}/{len(images)} API response format error")
                        results.append(self._get_default_result())
                else:
                    print(f"❌ Image {i+1}/{len(images)} API request failed, status: {response.status_code}")
                    print(f"❌ Error: {response.text}")
                    results.append(self._get_default_result())
                
                # 添加延迟避免请求过快
                if i < len(images) - 1:
                    time.sleep(0.5)
            
            end_time = time.time()
            total_time = end_time - start_time
            print(f"✅ All images analyzed - total elapsed: {total_time:.2f}s")
            
            return results
            
        except requests.exceptions.Timeout:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"⏰ API request timeout - elapsed: {total_time:.2f}s")
            return [self._get_default_result() for _ in images]
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"❌ API request error: {e} - elapsed: {total_time:.2f}s")
            return [self._get_default_result() for _ in images]
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"❌ Error during analysis: {e} - elapsed: {total_time:.2f}s")
            return [self._get_default_result() for _ in images] 