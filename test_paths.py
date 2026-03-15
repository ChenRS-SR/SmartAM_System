"""测试路径问题"""
import sys
sys.path.insert(0, 'backend')

import os
from pathlib import Path

# 1. 测试文件是否存在
calib_path = r'D:\FDM_Monitor_Diagnosis\SmartAM_System\calibration_points.json'
print(f'1. 标定文件路径: {calib_path}')
print(f'   文件存在: {os.path.exists(calib_path)}')

# 2. 测试从 backend 运行时的路径
backend_dir = Path('backend').resolve()
project_root = backend_dir.parent
print(f'\n2. Backend目录: {backend_dir}')
print(f'   项目根目录: {project_root}')
print(f'   标定文件: {project_root / "calibration_points.json"}')
print(f'   文件存在: {(project_root / "calibration_points.json").exists()}')

# 3. 测试畸变矫正器
try:
    from core.slm.distortion_corrector import DistortionCorrector
    corrector = DistortionCorrector()
    print(f'\n3. 畸变矫正器加载成功')
    print(f'   配置: {corrector.get_calibration_info()}')
except Exception as e:
    print(f'\n3. 畸变矫正器加载失败: {e}')

# 4. 测试扫描视频文件
simulation_dir = Path(r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record')
print(f'\n4. 模拟视频目录: {simulation_dir}')
print(f'   目录存在: {simulation_dir.exists()}')
if simulation_dir.exists():
    files = list(simulation_dir.glob('*.mp4'))
    print(f'   视频文件: {[f.name for f in files]}')
