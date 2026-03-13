"""
视频剪辑器
使用 FFmpeg 处理视频
"""
import subprocess
import os
from pathlib import Path


class VideoEditor:
    """视频剪辑工具"""
    
    def __init__(self, config=None):
        self.config = config or {
            "trim_start": 2,
            "trim_end": 1,
            "output_size": {"width": 1080, "height": 1350},
            "bitrate": "4M"
        }
        self.edited_dir = Path("videos/edited")
        self.edited_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_duration(self, video_path):
        """获取视频时长"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 0
    
    def edit_video(self, input_path, output_name=None):
        """
        剪辑视频：
        1. 裁剪开头结尾（去水印）
        2. 调整画幅为 4:5
        3. 压缩优化
        """
        input_path = Path(input_path)
        if not input_path.exists():
            print(f"文件不存在: {input_path}")
            return None
        
        duration = self.get_video_duration(input_path)
        if duration <= 0:
            print("无法获取视频时长")
            return None
        
        # 计算裁剪时间
        start = self.config.get("trim_start", 2)
        end = self.config.get("trim_end", 1)
        new_duration = duration - start - end
        
        if new_duration <= 0:
            print("视频太短，无法裁剪")
            return None
        
        # 输出文件名
        if not output_name:
            output_name = f"edited_{input_path.stem}.mp4"
        output_path = self.edited_dir / output_name
        
        width = self.config["output_size"]["width"]
        height = self.config["output_size"]["height"]
        bitrate = self.config.get("bitrate", "4M")
        
        print(f"🎬 开始剪辑: {input_path.name}")
        print(f"   原时长: {duration:.1f}s | 裁剪: +{start}s ~ -{end}s | 新时长: {new_duration:.1f}s")
        print(f"   输出分辨率: {width}x{height} | 码率: {bitrate}")
        
        # FFmpeg 命令
        # -vf: 视频滤镜 (裁剪时间 + 调整画幅)
        # crop=ih*4/5:ih 保持高度，按4:5裁剪宽度
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ss", str(start),
            "-t", str(new_duration),
            "-vf", f"crop=ih*{width}/{height}:ih,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264",
            "-b:v", bitrate,
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ 剪辑完成: {output_path}")
                return str(output_path)
            else:
                print(f"❌ FFmpeg 错误: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ 剪辑失败: {e}")
            return None
    
    def batch_edit(self, raw_dir="videos/raw"):
        """批量剪辑目录下的所有视频"""
        raw_path = Path(raw_dir)
        if not raw_path.exists():
            print(f"目录不存在: {raw_path}")
            return []
        
        results = []
        for video_file in raw_path.glob("*.mp4"):
            result = self.edit_video(video_file)
            if result:
                results.append(result)
        
        return results


def edit_single_video(input_path, config=None):
    """便捷函数"""
    editor = VideoEditor(config)
    return editor.edit_video(input_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        result = edit_single_video(path)
        print(f"输出: {result}")
    else:
        print("Usage: python editor.py <video_path>")
