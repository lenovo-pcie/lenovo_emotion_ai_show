import requests
import base64
import json
import re
from emotion_analyzer_base import EmotionAnalyzerBase
from emotion_analyzer_api.screen_content_class_config_loader import load_screen_content_class_config

class EmotionAnalyzerVolcengine(EmotionAnalyzerBase):
    def __init__(self, api_key, camera_backend=None, camera_index=0):
        super().__init__(api_key, camera_backend, camera_index, "Volcengine")
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        # 加载标准分类提示词
        _, self.screen_class_prompt = load_screen_content_class_config()
    
    def analyze_screen_content(self, screen_image):
        """分析屏幕截图内容，识别使用的APP和内容分类"""
        # 将OpenCV图像转为base64
        img_base64 = self.image_to_base64(screen_image)
        image_url = f"data:image/jpeg;base64,{img_base64}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "doubao-1-5-vision-pro-32k-250115",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "分析这张屏幕截图，识别以下信息并严格按照JSON格式返回：\n\n"
                                "{\n"
                                "  \"app_name\": \"应用名称\",\n"
                                "  \"app_category\": \"应用分类\",\n"
                                "  \"content_description\": \"10-15字描述\"\n"
                                "}\n\n"
                                f"{self.screen_class_prompt}\n\n"
                                "详细描述要求：\n"
                                "- 10-15字，简洁描述当前活动\n"
                                "- 如果图中有人物，请列出人物名字\n"
                                "- 如果是在看视频，请说明视频标题和主要人物\n"
                                "- 如果是聊天应用，请说明聊天对象和主题\n"
                                "- 如果是工作文档，请说明文档类型和主题\n\n"
                                "示例返回：\n"
                                "{\n"
                                "  \"app_name\": \"微信\",\n"
                                "  \"app_category\": \"社交\",\n"
                                "  \"content_description\": \"与张三聊天讨论会议\"\n"
                                "}\n\n"
                                "视频观看示例：\n"
                                "{\n"
                                "  \"app_name\": \"哔哩哔哩\",\n"
                                "  \"app_category\": \"娱乐\",\n"
                                "  \"content_description\": \"观看Python教程，讲师李四\"\n"
                                "}\n\n"
                                "如果无法识别应用，请返回：\n"
                                "{\n"
                                "  \"app_name\": \"未知应用\",\n"
                                "  \"app_category\": \"其他\",\n"
                                "  \"content_description\": \"无法识别当前应用和内容\"\n"
                                "}\n\n"
                                "重要：只返回JSON对象，不要其他任何文字！"
                            )
                        },
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        }
        
        try:
            import time
            start_time = time.time()
            print(f"🖥️ 正在调用Volcengine API分析屏幕内容...")
            
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            
            end_time = time.time()
            api_time = end_time - start_time
            
            content = result["choices"][0]["message"]["content"]
            
            # 提取JSON
            json_data = self._extract_json(content)
            if json_data:
                print(f"✅ 屏幕内容分析成功 - 耗时: {api_time:.2f}秒")
                print(f"   📱 应用: {json_data.get('app_name', '未知')}")
                print(f"   📂 分类: {json_data.get('app_category', '其他')}")
                print(f"   📝 描述: {json_data.get('content_description', '无描述')}")
                return json_data
            else:
                print(f"❌ 屏幕内容分析JSON解析失败: {content}")
                print(f"⚠️  API调用耗时: {api_time:.2f}秒")
                return self._get_default_screen_result()
                
        except Exception as e:
            print(f"❌ 屏幕内容分析失败: {e}")
            return self._get_default_screen_result()

    def analyze_emotion(self, images):
        """
        分析多张图片中的人物情绪，返回每张图片的情绪分析结果。
        返回格式：[{"has_face": bool, "emotion": str, "confidence": float, "emotion_level": float}]
        """
        results = []
        for image in images:
            # 将OpenCV图像转为base64
            img_base64 = self.image_to_base64(image)
            image_url = f"data:image/jpeg;base64,{img_base64}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": "doubao-1-5-vision-pro-32k-250115",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "分析图片中人物的情绪状态。你必须严格按照以下JSON格式返回，不要添加任何其他文字：\n\n"
                                    "{\n"
                                    "  \"has_face\": true,\n"
                                    "  \"emotion\": \"快乐\",\n"
                                    "  \"confidence\": 0.85,\n"
                                    "  \"emotion_level\": 0.6\n"
                                    "}\n\n"
                                    "规则说明：\n"
                                    "- has_face: 检测到人脸为true，否则为false\n"
                                    "- emotion: 只能是\"中立\"、\"快乐\"、\"愤怒\"、\"悲伤\"、\"惊讶\"、\"担忧\"、\"无\"中的一个\n"
                                    "- confidence: 0.0到1.0之间的数值，表示情绪识别的置信度\n"
                                    "- emotion_level: 0.0到1.0之间的数值，表示情绪强度\n"
                                    "\n"
                                    "情绪识别优先级（提高敏感度）：\n"
                                    "1. 快乐：任何微笑、嘴角上扬、眼睛微眯、面部放松等快乐迹象，即使非常轻微也要识别为快乐\n"
                                    "2. 愤怒：任何皱眉、嘴角下垂、眼神严肃、面部紧张等愤怒迹象，即使轻微也要识别为愤怒\n"
                                    "3. 悲伤：任何嘴角下垂、眼神黯淡、面部表情低落等悲伤迹象，即使轻微也要识别为悲伤\n"
                                    "4. 惊讶：任何眉毛上扬、眼睛睁大、嘴巴微张等惊讶迹象，即使轻微也要识别为惊讶\n"
                                    "5. 担忧：任何眉头微皱、眼神不安、面部表情紧张等担忧迹象，即使轻微也要识别为担忧\n"
                                    "6. 中立：只有在完全平静、无任何情绪迹象时才识别为中立\n"
                                    "\n"
                                    "情绪强度参考（提高敏感度）：\n"
                                    "- 快乐：任何快乐迹象0.3，轻微微笑0.5，明显微笑0.7，大笑0.9\n"
                                    "- 愤怒：任何愤怒迹象0.3，轻微皱眉0.5，明显愤怒0.7，极度愤怒0.9\n"
                                    "- 悲伤：任何悲伤迹象0.3，轻微低落0.5，明显悲伤0.7，极度悲伤0.9\n"
                                    "- 惊讶：任何惊讶迹象0.3，轻微惊讶0.5，明显惊讶0.7，极度惊讶0.9\n"
                                    "- 担忧：任何担忧迹象0.3，轻微担忧0.5，明显担忧0.7，极度担忧0.9\n"
                                    "- 中立：只有在完全无情绪时才为0.1，否则至少0.2\n"
                                    "\n"
                                    "如果没有检测到人脸，返回：\n"
                                    "{\"has_face\": false, \"emotion\": \"无\", \"confidence\": 0.0, \"emotion_level\": 0.0}\n\n"
                                    "重要：只返回JSON对象，不要其他任何文字！"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ]
            }
            try:
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                result = resp.json()
                #print("[Volcengine] 原始返回:", result)
                content = result["choices"][0]["message"]["content"]
                results.append({
                    "has_face": "无" not in content,
                    "emotion": self._extract_emotion(content),
                    "confidence": self._extract_confidence(content),
                    "emotion_level": self._extract_emotion_level(content)
                })
            except Exception as e:
                print(f"[Volcengine] Emotion analysis failed: {e}")
                results.append(self._get_default_result())
        return results

    def _extract_json(self, content):
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())
            return None
        except Exception:
            return None

    def _extract_emotion(self, content):
        data = self._extract_json(content)
        if data and 'emotion' in data:
            return data['emotion']
        for emo in ["中立", "快乐", "愤怒", "悲伤", "惊讶", "担忧", "无"]:
            if emo in content:
                return emo
        return "无"

    def _extract_confidence(self, content):
        data = self._extract_json(content)
        if data and 'confidence' in data:
            try:
                return float(data['confidence'])
            except Exception:
                return 0.0
        match = re.search(r"置信度[：: ]?([0-9.]+)", content)
        if match:
            try:
                return float(match.group(1))
            except:
                return 0.0
        return 0.0

    def _extract_emotion_level(self, content):
        data = self._extract_json(content)
        if data and 'emotion_level' in data:
            try:
                return float(data['emotion_level'])
            except Exception:
                return 0.0
        
        # 多种正则匹配模式
        patterns = [
            r"情绪强度[：: ]?([0-9.]+)",
            r"emotion_level[：: ]?([0-9.]+)",
            r"强度[：: ]?([0-9.]+)",
            r"level[：: ]?([0-9.]+)",
            r"情绪级别[：: ]?([0-9.]+)",
            r"级别[：: ]?([0-9.]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    print(f"[Volcengine] 提取到情绪强度: {value} (模式: {pattern})")
                    return value
                except:
                    continue
        
        # 如果没有找到，尝试根据情绪类型设置默认值（提高敏感度）
        emotion = self._extract_emotion(content)
        if emotion == "快乐":
            print("[Volcengine] 快乐情绪，设置默认强度: 0.6")
            return 0.6
        elif emotion in ["愤怒", "悲伤"]:
            print("[Volcengine] 负面情绪，设置默认强度: 0.7")
            return 0.7
        elif emotion == "惊讶":
            print("[Volcengine] 惊讶情绪，设置默认强度: 0.8")
            return 0.8
        elif emotion == "担忧":
            print("[Volcengine] 担忧情绪，设置默认强度: 0.5")
            return 0.5
        elif emotion == "中立":
            print("[Volcengine] 中立情绪，设置默认强度: 0.3")
            return 0.3
        else:
            print("[Volcengine] 未识别情绪，设置默认强度: 0.2")
            return 0.2

# 测试用例
if __name__ == "__main__":
    import cv2
    img = cv2.imread("test.jpg")
    analyzer = EmotionAnalyzerVolcengine(api_key="YOUR_API_KEY")
    print(analyzer.analyze_emotion([img])) 