"""
交互式视频编辑器
支持多种去重方案，用户可选择处理方式
"""
import json
import subprocess
import random
from pathlib import Path
from typing import Dict, List, Optional


class VideoEditor:
    """交互式视频剪辑器"""
    
    # 预设方案
    PRESETS = {
        "light": {
            "name": "轻度处理",
            "desc": "画幅转换 + 调速（适合原创内容）",
            "config": {
                "crop_top": 0,
                "crop_bottom": 0,
                "speed": 1.0,
                "hflip": False,
                "zoom": 1.0,
                "brightness": 0,
                "contrast": 0,
                "add_logo": False,
                "replace_audio": False
            }
        },
        "medium": {
            "name": "中度处理", 
            "desc": "镜像+缩放+调速+轻微调色（推荐）",
            "config": {
                "crop_top": 2,
                "crop_bottom": 1,
                "speed": 1.2,
                "hflip": True,
                "zoom": 1.05,
                "brightness": 0.05,
                "contrast": 0.1,
                "add_logo": False,
                "replace_audio": False
            }
        },
        "heavy": {
            "name": "重度处理",
            "desc": "全效果+Logo+换BGM（适合重复素材）",
            "config": {
                "crop_top": 2,
                "crop_bottom": 1,
                "speed": 1.25,
                "hflip": True,
                "zoom": 1.08,
                "brightness": 0.08,
                "contrast": 0.15,
                "saturation": 0.1,
                "add_logo": True,
                "replace_audio": True
            }
        }
    }
    
    def __init__(self, raw_dir="videos/raw", edited_dir="videos/edited", config_dir="videos/configs"):
        self.raw_dir = Path(raw_dir)
        self.edited_dir = Path(edited_dir)
        self.config_dir = Path(config_dir)
        
        for d in [self.raw_dir, self.edited_dir, self.config_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_video_info(self, video_path: Path) -> dict:
        """获取视频信息"""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,bit_rate",
            "-show_entries", "format=duration,size",
            "-of", "json",
            str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            stream = data.get("streams", [{}])[0]
            format_info = data.get("format", {})
            
            duration = float(stream.get("duration") or format_info.get("duration", 0))
            
            return {
                "width": stream.get("width", 0),
                "height": stream.get("height", 0),
                "duration": duration,
                "size_mb": int(format_info.get("size", 0)) / 1024 / 1024,
                "bitrate": stream.get("bit_rate", "unknown")
            }
        except Exception as e:
            print(f"⚠️  无法获取视频信息: {e}")
            return {}
    
    def load_config(self, note_id: str) -> Optional[dict]:
        """加载已保存的配置"""
        config_path = self.config_dir / f"{note_id}.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return None
    
    def save_config(self, note_id: str, config: dict):
        """保存配置"""
        config_path = self.config_dir / f"{note_id}.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def interactive_select(self, video_path: Path, note_id: str) -> dict:
        """交互式选择处理方案"""
        print(f"\n{'='*60}")
        print(f"🎬 视频: {video_path.name}")
        print(f"{'='*60}")
        
        # 显示视频信息
        info = self.get_video_info(video_path)
        if info:
            print(f"📊 信息: {info['width']}x{info['height']} | "
                  f"时长: {info['duration']:.1f}s | "
                  f"大小: {info['size_mb']:.1f}MB")
        
        # 检查是否有历史配置
        saved_config = self.load_config(note_id)
        if saved_config:
            print(f"\n💾 发现历史配置，使用预设: {saved_config.get('preset_name', '自定义')}")
            use_saved = input("   使用历史配置? (Y/n/custom): ").strip().lower()
            if use_saved in ['', 'y', 'yes']:
                return saved_config
        
        # 显示预设选项
        print(f"\n🎛️  请选择处理方案:")
        print("-" * 40)
        
        options = []
        for key, preset in self.PRESETS.items():
            options.append((key, preset))
            print(f"  {len(options)}. {preset['name']}")
            print(f"     {preset['desc']}")
        
        print(f"  {len(options)+1}. 自定义配置")
        print(f"  {len(options)+2}. 跳过不处理")
        print("-" * 40)
        
        choice = input("   选择 (1-5): ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                preset_key, preset = options[idx]
                config = preset["config"].copy()
                config["preset_key"] = preset_key
                config["preset_name"] = preset["name"]
                self.save_config(note_id, config)
                return config
            elif idx == len(options):
                return self.custom_config(note_id)
            else:
                return None  # 跳过
        except ValueError:
            return None
    
    def custom_config(self, note_id: str) -> dict:
        """自定义配置"""
        print(f"\n🔧 自定义配置:")
        
        config = {
            "preset_key": "custom",
            "preset_name": "自定义"
        }
        
        config["crop_top"] = int(input("   裁剪顶部秒数 (默认2): ") or "2")
        config["crop_bottom"] = int(input("   裁剪底部秒数 (默认1): ") or "1")
        config["speed"] = float(input("   播放速度 (1.0=原速, 1.2=1.2倍): ") or "1.0")
        config["hflip"] = input("   水平镜像? (y/N): ").strip().lower() == 'y'
        config["zoom"] = float(input("   缩放比例 (1.0=原图, 1.05=放大5%): ") or "1.0")
        config["brightness"] = float(input("   亮度调整 (-0.1~0.1, 默认0.05): ") or "0.05")
        config["contrast"] = float(input("   对比度调整 (-0.1~0.1, 默认0.1): ") or "0.1")
        
        self.save_config(note_id, config)
        return config
    
    def build_filter(self, config: dict, input_width: int, input_height: int) -> str:
        """构建 FFmpeg 滤镜"""
        filters = []
        
        # 1. 水平镜像
        if config.get("hflip", False):
            filters.append("hflip")
        
        # 2. 缩放（先放大再裁剪，实现去水印效果）
        zoom = config.get("zoom", 1.0)
        if zoom != 1.0:
            # 按比例放大，保持中心
            filters.append(f"scale=iw*{zoom}:ih*{zoom}")
        
        # 3. 裁剪为 4:5 比例 (1080x1350)
        # 计算裁剪区域，保持中心
        target_ratio = 4/5  # 0.8
        current_ratio = input_width / input_height
        
        if current_ratio > target_ratio:
            # 太宽了，裁剪两边
            new_width = int(input_height * target_ratio)
            x_offset = (input_width - new_width) // 2
            filters.append(f"crop={new_width}:ih:{x_offset}:0")
        else:
            # 太高了，裁剪上下
            new_height = int(input_width / target_ratio)
            y_offset = (input_height - new_height) // 2
            filters.append(f"crop=iw:{new_height}:0:{y_offset}")
        
        # 4. 调色
        brightness = config.get("brightness", 0)
        contrast = config.get("contrast", 0)
        saturation = config.get("saturation", 0)
        
        if brightness or contrast or saturation:
            # brightness: -1.0~1.0, contrast: -1000~1000, saturation: 0~3.0
            b_val = brightness  # FFmpeg eq 亮度范围
            c_val = 1.0 + contrast  # 对比度系数
            s_val = 1.0 + saturation if saturation else 1.0
            filters.append(f"eq=brightness={b_val}:contrast={c_val}:saturation={s_val}")
        
        # 5. 缩放到目标分辨率
        filters.append("scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2:black")
        
        return ",".join(filters) if filters else "copy"
    
    def edit_video(self, video_path: Path, config: dict) -> Optional[Path]:
        """执行视频剪辑"""
        note_id = video_path.stem
        output_path = self.edited_dir / f"edited_{note_id}.mp4"
        
        # 获取视频信息
        info = self.get_video_info(video_path)
        if not info:
            return None
        
        duration = info["duration"]
        crop_start = config.get("crop_top", 0)
        crop_end = config.get("crop_bottom", 0)
        new_duration = duration - crop_start - crop_end
        
        if new_duration <= 0:
            print("❌ 视频太短，无法裁剪")
            return None
        
        # 构建滤镜
        vf = self.build_filter(config, info["width"], info["height"])
        speed = config.get("speed", 1.0)
        
        print(f"\n🎬 开始剪辑:")
        print(f"   裁剪: +{crop_start}s ~ -{crop_end}s")
        print(f"   调速: {speed}x")
        print(f"   滤镜: {vf[:60]}...")
        
        # 构建 FFmpeg 命令
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]
        
        # 时间裁剪
        if crop_start > 0:
            cmd.extend(["-ss", str(crop_start)])
        if crop_end > 0 or crop_start > 0:
            cmd.extend(["-t", str(new_duration)])
        
        # 视频滤镜
        cmd.extend(["-vf", vf])
        
        # 调速（通过调整帧率实现）
        if speed != 1.0:
            cmd.extend(["-filter:v", f"setpts=PTS/{speed}", "-filter:a", f"atempo={min(speed, 2.0)}"])
        
        # 编码参数
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path)
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 获取输出文件信息
                out_info = self.get_video_info(output_path)
                print(f"✅ 剪辑完成: {output_path.name}")
                print(f"   输出: {out_info.get('size_mb', 0):.1f}MB | {out_info.get('duration', 0):.1f}s")
                return output_path
            else:
                print(f"❌ FFmpeg 错误: {result.stderr[:200]}")
                return None
        except Exception as e:
            print(f"❌ 剪辑失败: {e}")
            return None
    
    def process_single(self, video_path: Path, auto_preset: str = None) -> Optional[Path]:
        """处理单个视频"""
        note_id = video_path.stem
        
        # 检查是否已剪辑
        edited_path = self.edited_dir / f"edited_{note_id}.mp4"
        if edited_path.exists():
            print(f"⏭️  已存在剪辑版本: {edited_path.name}")
            reprocess = input("   重新处理? (y/N): ").strip().lower()
            if reprocess != 'y':
                return edited_path
        
        # 选择配置
        if auto_preset and auto_preset in self.PRESETS:
            config = self.PRESETS[auto_preset]["config"].copy()
            config["preset_key"] = auto_preset
            config["preset_name"] = self.PRESETS[auto_preset]["name"]
        else:
            config = self.interactive_select(video_path, note_id)
        
        if not config:
            print("⏭️  跳过处理")
            return None
        
        # 执行剪辑
        return self.edit_video(video_path, config)
    
    def batch_process(self, preset: str = None):
        """批量处理所有原始视频"""
        videos = list(self.raw_dir.glob("*.mp4"))
        if not videos:
            print("📭 raw 目录没有视频文件")
            return
        
        print(f"\n📦 发现 {len(videos)} 个视频")
        
        for video_path in videos:
            self.process_single(video_path, auto_preset=preset)
            print()


if __name__ == "__main__":
    import sys
    editor = VideoEditor()
    
    if len(sys.argv) > 1:
        # 处理指定视频
        path = Path(sys.argv[1])
        if path.exists():
            editor.process_single(path)
        else:
            print(f"❌ 文件不存在: {path}")
    else:
        # 批量处理
        editor.batch_process()
