"""默认读取封存输出；真实处理可选，失败按用户约定回到封存结果并仅记录日志。"""
from functools import lru_cache
from pathlib import Path
import io
import json
import logging
import hashlib
import threading
import zipfile
from .results import attach, format_result

ROOT=Path(__file__).resolve().parents[1]/'analysis_packages'
logger=logging.getLogger(__name__)

class AnalysisPackage:
    def __init__(self, case_id):
        self.root=ROOT/case_id
        self.meta=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        self.archived=json.loads((self.root/'results.json').read_text(encoding='utf-8'))
        for name,digest in self.meta['checksums'].items():
            if hashlib.sha256((self.root/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('分析包校验失败：'+name)
        self.live={}
        self.normal_checks={}
        self.runtime=None
        self.lock=threading.Lock()

    def inputs(self, layer):
        import numpy as np
        archive=next(item['archive'] for item in self.meta['layers'] if item['layer']==layer)
        with zipfile.ZipFile(self.root/archive) as pack:
            with np.load(io.BytesIO(pack.read(str(layer)+'.npz')),allow_pickle=False) as sample:
                return {key:sample[key] for key in sample.files}

    def compute(self, layer):
        if layer in self.live: return self.live[layer]
        # 定位到后段时仅计算当前显示窗口。封存包提供参照层编号，概率和贡献全部重新计算。
        if self.runtime is None:
            from .runtime import Runtime
            self.runtime=Runtime(self.meta['modelId'])
        if self.runtime.meta['sha256'] != self.meta['modelSha256']:
            raise ValueError('模型版本与案例输入规范不一致，请重新封存案例')
        item=next(r for r in self.meta['layers'] if r['layer']==layer)
        ref=self.archived[str(layer)]['row'].get('ref')
        reference=None
        if ref is not None:
            if ref>=layer: raise ValueError('参照层必须早于当前层')
            reference=self.inputs(ref)
            if ref not in self.normal_checks:
                self.normal_checks[ref]=self.runtime.infer(reference)
            check=self.normal_checks[ref]
            if check['p_proc']>=.5 or check['p_dev']>=.5:
                raise ValueError('参照层未通过当前模型正常性复核')
        output=self.runtime.infer(self.inputs(layer),reference)
        if ref is not None: output['ref']=ref
        self.live[layer]=format_result(self.meta,item,output)
        return self.live[layer]

    def apply(self, frame, rows, real=False):
        if not real and self.meta.get('preserveOriginalArchive'):
            frame['processing']={'real':False}
            return frame
        effective=real
        selected=self.archived
        if real:
            try:
                with self.lock:
                    arrived=[r['layer'] for r in rows if r['recognitionAt']<=frame['timestamp']]
                    for layer in arrived[-51:]: self.compute(layer)
                    selected={str(k):v for k,v in self.live.items()}
            except Exception:
                # UI 不说明切回原因；完整异常进入后端日志，离线输出来源保持可审计。
                logger.exception('设备 %s 真实处理不可用，切回封存结果',self.meta['device']['id'])
                effective=False
                if self.meta.get('preserveOriginalArchive'):
                    frame['processing']={'real':False}
                    return frame
                selected=self.archived
        attach(frame,selected,rows)
        frame['processing']={'real':effective}
        frame['analysisOrigin']='model-runtime' if effective else 'sealed-model-results'
        return frame

@lru_cache(maxsize=16)
def package(case_id):
    return AnalysisPackage(case_id)
