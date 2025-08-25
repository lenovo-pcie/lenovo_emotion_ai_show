import cv2
import requests
import json
import time
import base64
import io
from PIL import Image
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerZhipu(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=None, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "Zhipu")
        # Load standard screen classification prompt
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """Analyze screen content and classify app and content"""
        prompt = f"""分析这张屏幕截图，识别应用和内容。
特别注意：如果是电影电视剧等视频，必须分析出视频画面中的主要人物。

输出格式（必须严格按照以下JSON格式，不要任何其他内容）：
{{
    "app_name": "应用名称",
    "app_category": "应用分类", 
                "content_description": "10-15字描述"
}}

{self.screen_class_prompt}

内容描述（10-15字）：
- 简洁描述当前活动
- 如果是聊天，说明聊天对象和主题
- 如果是视频，必须分析视频画面中的主要人物，说明视频标题和画面中的主要人物
- 如果是文档，说明文档类型和主题

示例：
        {{"app_name": "微信", "app_category": "社交", "content_description": "与张三聊天讨论会议"}}

视频示例：
        {{"app_name": "哔哩哔哩", "app_category": "娱乐", "content_description": "观看Python教程，讲师李四"}}

无法识别时：
{{"app_name": "未知应用", "app_category": "其他", "content_description": "无法识别当前应用和内容"}}

重要：只输出JSON，不要任何解释、说明、代码块标记或其他内容。"""
        
        try:
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=self.api_key)
            
            # 准备图片的base64数据
            image_base64 = self.image_to_base64(screen_image)
            image_content = {
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        image_content
                    ]
                }
            ]
            
            start_time = time.time()
            print(f"🖥️ Calling Zhipu API to analyze screen content...")
            
            response = client.chat.completions.create(
                model="glm-4v-flash",
                messages=messages,
                extra_body={"temperature": 0.1, "max_tokens": 1024}
            )
            
            end_time = time.time()
            api_time = end_time - start_time
            
            # 智谱API返回格式
            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
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
                        print(f"❌ Failed to parse screen content JSON: {json_str}")
                        print(f"⚠️  API call elapsed: {api_time:.2f}s")
                        return self._get_default_screen_result()
                else:
                    print(f"❌ Screen content analysis did not return JSON: {content}")
                    print(f"⚠️  API call elapsed: {api_time:.2f}s")
                    return self._get_default_screen_result()
            else:
                print("❌ Screen content API response format error")
                print(f"⚠️  API call elapsed: {api_time:.2f}s")
                return self._get_default_screen_result()
                
        except ImportError:
            print("❌ zhipuai is not installed. Run: pip install zhipuai")
            return self._get_default_screen_result()
        except Exception as e:
            print(f"❌ Screen content analysis failed: {e}")
            return self._get_default_screen_result()
    
    def analyze_emotion(self, images):
        """Analyze emotions for multiple images using Zhipu API (per-image analysis)"""
        prompt = """分析这张图片中人物的情绪：

{
    \"has_face\": true/false,
    \"emotion\": \"中立/快乐/愤怒/悲伤/惊讶/担忧/无\",
    \"confidence\": 0.0-1.0,
    \"emotion_level\": 0.0-1.0
}

情绪识别规则：
- 所有情绪都应该得到平等对待，不要对任何特定情绪有偏见
- 根据面部表情、眼神、嘴角等特征客观识别情绪
- 情绪类型：中立、快乐、愤怒、悲伤、惊讶、担忧、无
- 重要：当表情平静、无明显情绪时，必须返回\"中立\"，不要返回\"中性\"
- 担忧情绪的识别要更加谨慎，只有在面部表情明显表现出担忧（如眉头紧锁、眼神忧虑等）时才判定为\"担忧\"，轻微表情不要判定为担忧

情绪强度：
- 0.0(无情绪) 0.3(轻微) 0.5(中等) 0.7(较强) 1.0(极强)
- 根据情绪表现的明显程度客观评估强度

无人脸时：has_face=false, emotion=\"无\", confidence=0.0, emotion_level=0.0

只返回JSON，不要其他内容。"""
        
        try:
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=self.api_key)
            
            results = []
            start_time = time.time()
            
            print(f"🌐 Calling Zhipu API to analyze {len(images)} images...")
            
            for i, image in enumerate(images):
                # 准备单张图片的base64数据
                image_base64 = self.image_to_base64(image)
                image_content = {
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            image_content
                        ]
                    }
                ]
                
                response = client.chat.completions.create(
                    model="glm-4v-flash",
                    messages=messages,
                    extra_body={"temperature": 0.1, "max_tokens": 1024}  # 降低temperature提高一致性
                )
                
                # 智谱API返回格式
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        try:
                            result_data = json.loads(json_str)
                            # 后处理：只增强快乐情绪的识别
                            # if result_data.get("emotion") == "快乐":
                            #     if result_data.get("confidence", 0) < 0.3:
                            #         result_data["confidence"] = 0.3
                            #     if result_data.get("emotion_level", 0) < 0.3:
                            #         result_data["emotion_level"] = 0.3
                            results.append(result_data)
                            print(f"✅ Image {i+1}/{len(images)} analyzed successfully")
                        except json.JSONDecodeError:
                            print(f"❌ Image {i+1}/{len(images)} JSON parse failed: {json_str}")
                            results.append(self._get_default_result())
                    else:
                        print(f"❌ Image {i+1}/{len(images)} did not return JSON: {content}")
                        results.append(self._get_default_result())
                else:
                    print(f"❌ Image {i+1}/{len(images)} API response format error")
                    results.append(self._get_default_result())
            
            end_time = time.time()
            api_time = end_time - start_time
            print(f"✅ All images analyzed - total elapsed: {api_time:.2f}s")
            return results
            
        except ImportError:
            print("❌ zhipuai is not installed. Run: pip install zhipuai")
            return [self._get_default_result() for _ in images]
        except Exception as e:
            print(f"❌ Zhipu API call failed: {e}")
            return [self._get_default_result() for _ in images]
