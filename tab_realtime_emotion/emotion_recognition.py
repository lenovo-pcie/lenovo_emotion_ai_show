import argparse
import os
import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModel, AutoFeatureExtractor
import os.path as osp
from models import get_models  

# 模型和特征提取相关配置
CLIP_MODEL = "clip-vit-large-patch14"
EMOTIONS = ["neutral", "angry", "happy", "sad", "worried", "surprise"]  # 情感标签

def load_feature_extractor(model_name):
    """加载预训练特征提取模型"""
    if model_name == CLIP_MODEL:
        model_dir = r"D:/emotion_model/clip-vit-large-patch14"  # 替换为实际路径
        model = AutoModel.from_pretrained(model_dir, local_files_only=True)
        model.cuda(0)
        feature_extractor = AutoFeatureExtractor.from_pretrained(model_dir)
        return model, feature_extractor
    

def extract_visual_features(clip_path, model, feature_extractor):
    """从clip0.npy提取视觉特征"""
    # 读取帧数据（假设格式为 [帧数, H, W, 3] BGR）
    frames = np.load(clip_path)
    if len(frames.shape) != 4:
        raise ValueError(f"clip0.npy格式错误，需为[帧数, H, W, 3]，实际为{frames.shape}")
    T, H, W, C = frames.shape
    print(f"帧数={T}, 高={H}, 宽={W}")
    
    # 转换为RGB并预处理
    images = [Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) for frame in frames]
    inputs = feature_extractor(images=images, return_tensors="pt")["pixel_values"].cuda()
    
    # 提取特征并聚合
    with torch.no_grad():
        frame_features = model.get_image_features(inputs)  # [帧数, 768]
    utterance_feature = torch.mean(frame_features, dim=0).unsqueeze(0)  # [1, 768]
    return utterance_feature

def extract_visual_features_from_faces(faces, model, feature_extractor):
    """
    从人脸帧列表提取视觉特征并聚合，返回 [1, 768] 的 torch.Tensor
    faces: List[np.ndarray]，每个元素为BGR格式的224x224人脸帧
    """
    if not faces or len(faces) == 0:
        raise ValueError("输入的人脸帧列表为空")
    # 转换为RGB并预处理
    images = [Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB)) for face in faces]
    inputs = feature_extractor(images=images, return_tensors="pt")["pixel_values"].cuda()
    # 提取特征并聚合
    with torch.no_grad():
        frame_features = model.get_image_features(inputs)  # [帧数, 768]
    utterance_feature = torch.mean(frame_features, dim=0).unsqueeze(0)  # [1, 768]
    return utterance_feature


def extract_visual_features_frame(image_path, model, feature_extractor):
    """  从单张 jpg/png 提取 768 维视觉特征，返回形状 [1, 768] 的 torch.Tensor。
    与 extract_visual_features 的输出维度一致，可直接拼接。  """

     # 1. 读图（OpenCV 默认为 BGR）
    _bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if _bgr is None:
        raise ValueError(f"无法读取图像：{image_path}")

     # 2. BGR → RGB → PIL
    _rgb = cv2.cvtColor(_bgr, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(_rgb)
    
    # 3. 预处理并移到 GPU（与之前函数保持一致）
    device = next(model.parameters()).device      # 跟随模型所在设备
    inputs = feature_extractor(images=image_pil, return_tensors="pt")["pixel_values"].to(device)

    # 4. 前向提特征
    with torch.no_grad():
        frame_feature = model.get_image_features(inputs)  # [1, 768]
    return frame_feature


def load_prediction_model(model_path, gpu=1):
    """加载训练好的分类模型"""
    torch.cuda.set_device(gpu)
    
    args_dir = osp.dirname(model_path)
    load_args_path = osp.join(args_dir, "best_args.npy")
    load_args = np.load(load_args_path, allow_pickle=True).item()["args"]
    args = load_args

    model = get_models(args).cuda()
    # 加载权重
    model.load_state_dict(
        torch.load(model_path, map_location=f"cuda:{gpu}", weights_only=True)
        )
    
    print("load model: {} \n".format(args.model))
    print("load model weight: {} \n".format(model_path))
    model.eval()
    return model


def predict_single_clip(clip_path, model_path=None, model=None, feature_model=CLIP_MODEL, feat_model=None, processor=None, gpu=0):
    """完整流程：提取特征 -> 模型预测 -> 返回分类结果
    支持已加载模型对象，避免重复加载权重。
    """
    # 1. 提取视觉特征
    print("提取视觉特征...")
    # feat_model, processor = load_feature_extractor(feature_model)
    visual_feat = extract_visual_features_frame(clip_path, feat_model, processor)
    print(f"visual_feat shape:{visual_feat.shape}") # torch.Size([1, 768])
    audio_feat = visual_feat  # 网络中音频特征为视觉特征
    print(f"audio_feat shape:{audio_feat.shape}") # torch.Size([1, 768])

    # 2. 加载分类模型（优先用已加载模型对象）
    if model is None:
        if model_path is None:
            raise ValueError("model和model_path不能同时为None")
        print("加载分类模型...")
        model = load_prediction_model(model_path, gpu)
    else:
        print("使用已加载模型对象...")

    # 3. 预测
    print("进行预测...")

    batch = {}
    batch["videos"] = visual_feat.float().cuda()
    batch["audios"] = audio_feat.float().cuda()
    
    with torch.no_grad():
        _, emos_out, _, _ = model(batch)

    # 4. 解析结果
    prob = torch.softmax(emos_out, dim=1).cpu().numpy()[0]  # 概率归一化
    pred_idx = np.argmax(prob)
    pred_label = EMOTIONS[pred_idx]
    
    return {
        "预测情感": pred_label,
        "情感概率": {EMOTIONS[i]: float(prob[i]) for i in range(len(EMOTIONS))},
        "置信度": float(prob[pred_idx])
    }



# predict_single_clip 支持传入已加载的 feat_model、processor、model
def predict_single_clip_yolo(
    faces,
    model_path=None,
    model=None,
    feature_model=CLIP_MODEL,
    feat_model=None,
    processor=None,
    gpu=0
):
    """完整流程：提取特征 -> 模型预测 -> 返回分类结果"""
    # 1. 提取视觉特征
    if feat_model is None or processor is None:
        feat_model, processor = load_feature_extractor(feature_model)
    visual_feat = extract_visual_features_from_faces(faces, feat_model, processor)
    audio_feat = visual_feat

    # 2. 加载分类模型（优先用已加载模型对象）
    if model is None:
        if model_path is None:
            raise ValueError("model和model_path不能同时为None")
        model = load_prediction_model(model_path, gpu)

    batch = {}
    batch["videos"] = visual_feat.float().cuda()
    batch["audios"] = audio_feat.float().cuda()

    with torch.no_grad():
        _, emos_out, _, _ = model(batch)

    prob = torch.softmax(emos_out, dim=1).cpu().numpy()[0]
    pred_idx = np.argmax(prob)
    pred_label = EMOTIONS[pred_idx]

    return {
        "预测情感": pred_label,
        "情感概率": {EMOTIONS[i]: float(prob[i]) for i in range(len(EMOTIONS))},
        "置信度": float(prob[pred_idx])
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    feat_model, processor = load_feature_extractor("clip-vit-large-patch14")
    parser.add_argument("--clip_path", default=r"D:/workspace/emo_demo_v1/data/face_4.jpg", help="输入的clip0.npy路径")
    parser.add_argument("--model_path", default=r"D:/emotion_model/AV_Base_v3/2025-07-22-14-04-04/best.pth", help="训练好的模型权重路径（如best.pth）")
    parser.add_argument("--gpu", type=int, default=0, help="使用的GPU编号")
    args = parser.parse_args()
    
    # 执行预测
    result = predict_single_clip(
        clip_path=args.clip_path,
        model_path=args.model_path,
        model=None,  # 不传模型对象，使用默认加载
        feature_model=CLIP_MODEL,
        feat_model=feat_model,  # 不传特征提取模型，使用默认加载
        processor=processor,  # 不传处理器，使用默认加载
        gpu=args.gpu
    )
    
    # 输出结果
    print("\n===== 预测结果 =====")
    print(f"预测情感标签: {result['预测情感']}")
    print("各情感概率:")
    for emo, p in result["情感概率"].items():
        print(f"  {emo}: {p:.4f}")
    print(f"置信度: {result['置信度']:.4f}")
