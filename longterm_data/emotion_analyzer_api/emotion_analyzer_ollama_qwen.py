import cv2
import requests
import json
import time
import base64
import io
from PIL import Image
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerOllamaQwen(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=0, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "Ollama-Qwen")
        # api_key 在这里作为 ollama 服务的基础URL
        self.base_url = api_key if api_key.startswith('http') else f"http://{api_key}:11434"
        self.model_name = "qwen2.5vl:7b"  # 使用qwen2.5vl:7b模型，支持图像分析
        # 加载标准分类提示词
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """分析屏幕截图内容，识别使用的APP和内容分类"""
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
            "Content-Type": "application/json"
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
            print(f"🖥️ 正在调用Ollama API分析屏幕内容...")
            
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
        """使用Ollama API分析多张图像中的情绪"""
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
            "Content-Type": "application/json"
        }
        
        results = []
        start_time = time.time()
        
        try:
            print(f"🌐 正在调用Ollama API分析 {len(images)} 张图片...")
            
            for i, image in enumerate(images):
                # 准备单张图片的base64数据
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
                
                # 调试：打印请求数据的前100个字符
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
                
                # 添加延迟避免请求过快
                if i < len(images) - 1:
                    time.sleep(0.5)
            
            end_time = time.time()
            total_time = end_time - start_time
            print(f"✅ 所有图片分析完成 - 总耗时: {total_time:.2f}秒")
            
            return results
            
        except requests.exceptions.Timeout:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"⏰ API请求超时 - 耗时: {total_time:.2f}秒")
            return [self._get_default_result() for _ in images]
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"❌ API请求异常: {e} - 耗时: {total_time:.2f}秒")
            return [self._get_default_result() for _ in images]
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"❌ 分析过程中出现错误: {e} - 耗时: {total_time:.2f}秒")
            return [self._get_default_result() for _ in images] 