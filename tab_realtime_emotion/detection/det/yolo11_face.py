from ultralytics import YOLO
import numpy as np
import cv2
import os

class YOLOFace:
    def __init__(self, args=None, weight_path='weights/detector/model_11n.pt'):
        # 加载训练模型
        self.model = YOLO(weight_path)
        self.conf=args.conf_thres if args else 0.5

    def predict(self, image):
        """
        image: 可为图像路径、PIL图像、NumPy数组或 OpenCV 图像。
        conf: 置信度阈值。
        """
        results = self.model.predict(image, save=False, imgsz=640, conf=self.conf, verbose=False)

        cls_ids = results[0].boxes.cls.cpu().numpy()
        cls_conf = results[0].boxes.conf.cpu().numpy()
        # x1y1x2y2转xywh
        bbox_xyxy = results[0].boxes.data[..., :4].cpu().numpy()
        bbox_xywh = np.stack([
            (bbox_xyxy[:, 0] + bbox_xyxy[:, 2]) / 2,
            (bbox_xyxy[:, 1] + bbox_xyxy[:, 3]) / 2,
            bbox_xyxy[:, 2] - bbox_xyxy[:, 0],
            bbox_xyxy[:, 3] - bbox_xyxy[:, 1]
        ], axis=1)
        
        return bbox_xyxy, bbox_xywh, cls_ids, cls_conf

# 示例使用
if __name__ == '__main__':
    # detector = YOLOFace(weight_path='weights/detector/feryolo-11x-64.pt')
    detector = YOLOFace()

    img_path = ['bus.jpg',
                # '/home/lenovo/New/UnionProject/test/IMDB_wiki/wiki_crop/14/639714_1923-10-25_1948.jpg',
                # '/home/lenovo/New/UnionProject/test/IMDB_wiki/wiki_crop/14/1204314_1962-03-03_2003.jpg',
                # '/home/lenovo/New/UnionProject/test/IMDB_wiki/wiki_crop/14/2009614_1964-05-13_2008.jpg',
                # '/home/lenovo/New/UnionProject/test/IMDB_wiki/wiki_crop/14/4419514_1929-07-17_2007.jpg'
                ]
    img_index = 0
    bbox_xyxy, bbox_xywh, cls_ids, cls_conf = detector.predict(img_path[img_index])
    print(bbox_xyxy)
    img = cv2.imread(img_path[img_index])
    os.makedirs('saved_imgs', exist_ok=True)

    box = bbox_xyxy[0]
    x1, y1, x2, y2 = map(int, box)
    face = img[y1:y2, x1:x2]
    face_resized = cv2.resize(face, (112, 112))
    cv2.imwrite(f'saved_imgs/face_{img_index}.jpg', face_resized)
    # import cv2
    # cap = cv2.VideoCapture('/home/lenovo/New/UnionProject/test/MOT17-08.mp4')
    # ret, frame = cap.read()
    # cap.release()

    # if ret:
    #     cv2.imwrite('first_frame.jpg', frame)
    #     results = detector.predict(frame)
    # else:
    #     raise RuntimeError("Failed to read the first frame from the video.")
    
    # results[0].show()
