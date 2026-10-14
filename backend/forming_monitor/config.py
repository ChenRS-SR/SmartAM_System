"""路径与运行配置。全部可用环境变量覆盖，界面与接口响应中不出现任何文件路径。"""
from __future__ import annotations

import os
from pathlib import Path

PKG = Path(__file__).resolve().parent
BACKEND = PKG.parent


def _p(env: str, default) -> Path:
    return Path(os.environ.get(env, str(default))).expanduser()


# 设备清单、设备照片、结果回放包
PACK_DIR = _p('FORMING_PACK_DIR', BACKEND / 'data_pack')
# 识别模型包（tools/export_model_bundle.py 导出）。独立运行时在 backend/model_bundle/，集成进 SmartAM 后放在 backend/weights/（已被 git 忽略）
MODEL_DIR = _p('FORMING_MODEL_DIR', BACKEND / 'model_bundle' if (BACKEND / 'model_bundle').is_dir() else BACKEND / 'weights')
# 运行缓存（识别概率、零件区、博弈结果、缩放后的图像），删除后自动重算
CACHE_DIR = _p('FORMING_CACHE_DIR', BACKEND / '.cache' / 'forming')
# 推理设备：cpu / cuda / auto
TORCH_DEVICE = os.environ.get('FORMING_DEVICE', 'cpu')

# 离线回放的数据根目录（现场设备原始导出数据与第四章预处理结果，只读）
SITE_RAW_ROOT = _p('FORMING_SITE_RAW', '/home/gjw/博士论文工作/phd_thesis_Markdown/章节数据/06-第六章真实工厂数据/7103_factory_dataset_v1')
SITE_PRE_ROOT = _p('FORMING_SITE_PRE', '/home/gjw/博士论文工作/phd_thesis_Markdown/章节数据终稿/04-迁移泛化数据/7103')

# 离线回放：逐层接入的回放间隔（秒/层）
REPLAY_INTERVAL = float(os.environ.get('FORMING_REPLAY_INTERVAL', '3'))

# 界面显示的运行状态文字。系统默认如实显示“离线回放”；论文示意截图时用 FORMING_MODE_LABEL=在线 启动（见 ../出截图.sh），
# 此时 status.mode 仍为 replay，数据仍是现场导出数据的逐层回放。
MODE_LABEL = os.environ.get('FORMING_MODE_LABEL', '离线回放')
