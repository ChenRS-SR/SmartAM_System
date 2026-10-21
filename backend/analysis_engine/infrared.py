"""M130 铺粉后红外独立识别；不将可见光分区掩膜冒用为红外配准结果。"""
import hashlib
import io
import json
from pathlib import Path
import threading
import cv2
import numpy as np
from PIL import Image
import torch


class InfraredRuntime:
    def __init__(self):
        from .runtime import VisionDual
        root = Path(__file__).resolve().parents[1]/'inference_models'
        self.meta = json.loads((root/'registry.json').read_text(encoding='utf-8'))['m130-ir-before']
        weights = root/self.meta['file']
        if hashlib.sha256(weights.read_bytes()).hexdigest() != self.meta['sha256']:
            raise ValueError('红外权重校验失败')
        self.model = VisionDual(len(self.meta['classes']))
        self.model.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True))
        self.model.eval()
        self.lock = threading.Lock()

    def predict(self, encoded):
        from .runtime import MEAN, STD
        with Image.open(io.BytesIO(encoded.tobytes())) as image:
            raw = np.asarray(image.convert('RGB'), dtype=np.float32)
        values = raw.reshape(-1, 3)
        deviation = values.std(0)
        if np.any(deviation <= 0): raise ValueError('红外帧通道标准差无效')
        norm = self.meta['normalization']
        # 与训练一致：红外全画幅逐通道归一化，再缩放；没有温度标定，不产生摄氏度读数。
        rgb = np.clip((raw-values.mean(0))/deviation*np.asarray(norm['std'],np.float32)+np.asarray(norm['mean'],np.float32),0,255)
        rgb = cv2.resize(rgb,(224,224),interpolation=cv2.INTER_AREA)
        x = torch.from_numpy((rgb.transpose(2,0,1)/255-MEAN)/STD)[None]
        with self.lock, torch.inference_mode():
            probabilities = self.model(x).softmax(1)[0].numpy()
        best = int(probabilities.argmax())
        return {'label':self.meta['classes'][best], 'confidence':float(probabilities[best]),
                'anomalyProbability':float(1-probabilities[self.meta['classes'].index('正常')]),
                'classes':[{'name':name,'p':float(p)} for name,p in zip(self.meta['classes'],probabilities)],
                'modelVersion':self.meta['sha256']}
