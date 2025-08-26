import numpy as np
import cv2
import os
# from insightface.utils import face_align
from PIL import Image
from typing import Union, List, Tuple
import onnxruntime as ort

class FaceAttr:
    def __init__(self, model_name='Age', device: str = "cuda", args=None):
        # os.environ['LD_LIBRARY_PATH'] = '/media/lenovo/ce79d608-7210-414a-a971-bfeb5d58d04c/usr/local/cuda-11.3/targets/x86_64-linux/lib:' + os.environ.get('LD_LIBRARY_PATH', '')

        """
        初始化 DeepFace 模型，只支持已下载好的四个模型。
        """
        self.model_name = model_name
        self.device = device
        self.reid_input = 'prior_patch'
        self.input_resize_size=(224,224)
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

        self.age_session = ort.InferenceSession("weights/attribution_DeepFace/age_model.onnx", providers=providers)
        self.gender_session = ort.InferenceSession("weights/attribution_DeepFace/gender_model.onnx", providers=providers)
        # self.emotion_session = ort.InferenceSession("weights/attribution_DeepFace/emotion_model.onnx", providers=providers)
        self.race_session = ort.InferenceSession("weights/attribution_DeepFace/race_model.onnx", providers=providers)


    def from_dict(self, data):
        bboxes = data["bboxes"]
        kpss = None
        if all(key in data and data[key] is not None for key in ["left_eye", "right_eye", "nose", "left_mouth", "right_mouth"]):
            kpss = np.stack([
                np.array(data["left_eye"]),
                np.array(data["right_eye"]),
                np.array(data["nose"]),
                np.array(data["left_mouth"]),
                np.array(data["right_mouth"])
            ], axis=0).transpose(1, 0, 2)  # shape: (n, 5, 2)
        return bboxes, kpss
    
    def extract_with_location(self, img: Image.Image, face_info: dict = None, align_face: bool = False) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
        """
        注意:
        这里输入的原始图像, 不是剪切后的patch(因为脸部的五官点采用的是原图的坐标)
        """
        bboxes, kpss = self.from_dict(face_info)
        embeddings = []
        preprocessed_images = []
        for i in range(bboxes.shape[0]):
            if align_face:
                assert kpss is not None, "kpss must be provided for face alignment"
                # 对人脸进行对齐
                aimg = face_align.norm_crop(img, landmark=kpss[i], image_size=224)
            else:
                x1, y1, x2, y2 = [max(0, int(coord)) for coord in bboxes[i][:-1]]
                aimg = img[y1:y2, x1:x2]
                aimg = cv2.resize(aimg, self.input_resize_size)
            preprocessed_images.append(aimg)
            
        preprocessed_images = np.array(preprocessed_images)
        # img = img.astype(np.float32) / 255.0
        age_output = self.age_session.run(None, {self.age_session.get_inputs()[0].name: preprocessed_images})
        gender_output = self.gender_session.run(None, {self.gender_session.get_inputs()[0].name: preprocessed_images})
        race_output = self.race_session.run(None, {self.race_session.get_inputs()[0].name: preprocessed_images})

        imgs_list = []
        for i in range(len(preprocessed_images)):
            img_gray = cv2.cvtColor(preprocessed_images[i], cv2.COLOR_BGR2GRAY)
            img_gray = cv2.resize(img_gray, (48, 48))
            imgs_list.append(img_gray)
        processed_imgs = np.expand_dims(np.array(imgs_list), axis=-1)

        # emotion_output = self.emotion_session.run(None, {self.emotion_session.get_inputs()[0].name: processed_imgs})
        # apparent_emotion = np.argmax(emotion_output)
        output_indexes = np.arange(0, 101)
        face_info['age'] = np.sum(age_output[0] * output_indexes[None, :], axis=1)
        # face_info['emotion'] = emotion_output[0]
        face_info['gender'] = gender_output[0]
        face_info['race'] = race_output[0]

        return face_info


if __name__ == '__main__':
    from PIL import Image
    import cv2
    import sys
    

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.append(project_root)

    # from model.detector.insight_det import Insight_FaceDet

    # detector = Insight_FaceDet()
    model = FaceAttr()

    img_path = "bus.jpg"
    img = cv2.imread(img_path)

    # result = detector.predict(img)
    result = {"bboxes": np.array([[0, 0, 224, 224, 1]])}  # 模拟人脸检测结果
    img = img.astype(np.float32) / 255.0
    for i in range(1000):
        feat = model.extract_with_location(img, result)

    for key, value in feat.items():
        if isinstance(value, np.ndarray):
            print(f"{key}: shape={value.shape}")
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], np.ndarray):
            print(f"{key}: list of arrays, first shape={value[0].shape}")
        else:
            print(f"{key}: type={type(value)}")

