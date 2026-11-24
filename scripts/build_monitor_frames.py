"""将已矫正视频离线抽为每秒一帧；部署端只加载 JPEG，不依赖视频解码。"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_frames():
    for channel in sorted((ROOT / 'slm_device_data' / 'SLM').glob('*/mock_video_corrected/CH[13]')):
        videos = sorted(p for p in channel.iterdir() if p.suffix.lower() in ('.mp4', '.webm', '.mov', '.m4v', '.ogg'))
        if not videos:
            continue
        source = videos[0]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target = channel / 'frames'
        manifest = target / 'manifest.json'
        if manifest.exists():
            info = json.loads(manifest.read_text())
            if info['sourceSha256'] == digest and all((target / f'{i:06d}.jpg').is_file() for i in range(1, info['count'] + 1)):
                continue
        target.mkdir(exist_ok=True)
        # 只清理本脚本生成的帧，原始及矫正视频均保留。
        for old in target.glob('[0-9][0-9][0-9][0-9][0-9][0-9].jpg'):
            old.unlink()
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                        '-vf', 'fps=1', '-q:v', '3', str(target / '%06d.jpg')], check=True)
        count = len(list(target.glob('*.jpg')))
        if not count:
            raise ValueError(f'未抽出图像: {source}')
        manifest.write_text(json.dumps(dict(source=source.name, sourceSha256=digest, count=count, intervalMs=1000), indent=2) + '\n')
        print(source.relative_to(ROOT), count)


if __name__ == '__main__':
    build_frames()
