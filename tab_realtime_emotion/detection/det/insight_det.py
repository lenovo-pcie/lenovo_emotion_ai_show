import glob
import os.path as osp

import numpy as np
import onnxruntime
from insightface.model_zoo import model_zoo

import torch
from insightface.utils import ensure_available
import cv2


class Insight_FaceDet:
    def __init__(self, name='buffalo_l', root='weights/ReID/insightface', allowed_modules=['detection'], args=None, **kwargs):
        device = args.device if args is not None else 'cuda' if torch.cuda.is_available() else 'cpu'
        # TODO: 可能之后修改
        # det_size=args.det_size if args is not None else (640, 640)
        det_size=(640, 640)

        self.models = {}
        onnxruntime.set_default_logger_severity(3)
        self.model_dir = ensure_available('models', name, root=root)
        onnx_files = glob.glob(osp.join(self.model_dir, '*.onnx'))
        onnx_files = sorted(onnx_files)
        for onnx_file in onnx_files:
            model = model_zoo.get_model(onnx_file, **kwargs)
            if model is None:
                print('model not recognized:', onnx_file)
            elif allowed_modules is not None and model.taskname not in allowed_modules:
                print('model ignore:', onnx_file, model.taskname)
                del model
            elif model.taskname not in self.models and (allowed_modules is None or model.taskname in allowed_modules):
                print('find model:', onnx_file, model.taskname, model.input_shape, model.input_mean, model.input_std)
                self.models[model.taskname] = model
            else:
                print('duplicated model task type, ignore:', onnx_file, model.taskname)
                del model
        assert 'detection' in self.models
        self.det_model = self.models['detection']
        self.prepare(ctx_id=0 if device == 'cuda' else -1, det_size=det_size)

    def to_dict(self, bboxes, kpss=None):
        return {
            "bboxes": bboxes,
            "left_eye": kpss[:, 0] if kpss is not None else None,
            "right_eye": kpss[:, 1] if kpss is not None else None,
            "nose": kpss[:, 2] if kpss is not None else None,
            "left_mouth": kpss[:, 3] if kpss is not None else None,
            "right_mouth": kpss[:, 4] if kpss is not None else None,
        }
    
    def prepare(self, ctx_id, det_thresh=0.5, det_size=(640, 640)):
        self.det_thresh = det_thresh
        assert det_size is not None
        print('set det-size:', det_size)
        self.det_size = det_size
        for taskname, model in self.models.items():
            if taskname=='detection':
                model.prepare(ctx_id, input_size=det_size, det_thresh=det_thresh)
            else:
                model.prepare(ctx_id)
    
    def predict(self, img, max_num=10, det_metric='default'):
        bboxes, kpss = self.det_model.detect(img,
                                             max_num=max_num,
                                             metric=det_metric)
        # if bboxes.shape[0] == 0:
        #     return []
        # ret = []
        # for i in range(bboxes.shape[0]):
        #     bbox = bboxes[i, 0:4]
        #     det_score = bboxes[i, 4]
        #     kps = None
        #     if kpss is not None:
        #         kps = kpss[i]
        #     face = Face(bbox=bbox, kps=kps, det_score=det_score)
        #     for taskname, model in self.models.items():
        #         if taskname=='detection':
        #             continue
        #         model.get(img, face)
        #     ret.append(face)
        res = self.to_dict(bboxes, kpss)
        return res
    

if __name__ == "__main__":

    # 加载测试图片

    fa = Insight_FaceDet()
    img_path = "/home/lenovo/New/UnionProject/test/bus.jpg"
    img = cv2.imread(img_path)
    for i in range(300):
        if img is None:
            print(f"无法加载图片: {img_path}")
        else:
            result = fa.predict(img)
            print("检测结果:", result)