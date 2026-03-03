"""
PacNet 推理模块测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_import():
    """测试模块导入"""
    try:
        from core.pacnet_inference import PacNetInference, get_inference_engine
        print("✓ 模块导入成功")
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        raise


def test_inference_class():
    """测试推理类初始化"""
    # from core.pacnet_inference import PacNetInference
    # 注意：这里需要一个实际的模型路径才能测试
    # engine = PacNetInference("dummy_path.pth")
    pass


if __name__ == "__main__":
    test_import()
    print("所有测试通过！")
