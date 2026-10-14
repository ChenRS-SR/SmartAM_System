"""数据源：把设备的逐层数据（图像、扭矩、状态参数、报警）以统一结构提供给服务层。

现阶段为离线回放（读取现场设备导出的原始数据）；接入实时数据时实现同样的方法即可，见 base.DataSource。
"""
from .base import DataSource, LayerInputs  # noqa: F401
