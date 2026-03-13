"""
高级视频编辑器 - v2.1
修复首帧冻结，改为 9:16 比例
"""
import json
import subprocess
from pathlib import Path


class AdvancedVideoEditor:
    """高级视频剪辑器 v2.1"""
    
    PRESETS = {
        "light": {"name": "轻度", "desc": "画幅+调速",
            "config": {"crop_top": 0, "crop_bottom": 0, "speed": 1.0, "hflip": False, "zoom": 1.0,
                "brightness": 0, "contrast": 0, "saturation": 0,
                "add_logo": False, "replace_audio": False, "original_volume": 1.0}},
        "medium": {"name": "中度", "desc": "镜像+缩放+调色+Logo",
            "config": {"crop_top": 0.5, "crop_bottom": 0.5, "speed": 1.05, "hflip": True, "zoom": 1.05,
                "brightness": 0.05, "contrast": 0.1, "saturation": 0.05,
                "add_logo": True, "logo_select": "logo_default.png", "logo_position": "bottom_right",
                "logo_size": 0.10, "logo_opacity": 0.85,
                "replace_audio": False, "original_volume": 1.0}},
        "heavy": {"name": "重度", "desc": "全效果+BGM+Logo",
            "config": {"crop_top": 2, "crop_bottom": 1, "speed": 1.25, "hflip": True, "zoom": 1.08,
                "brightness": 0.08, "contrast": 0.15, "saturation": 0.1,
                "add_logo": True, "logo_select": "logo_default.png", "logo_position": "bottom_center", 
                "logo_size": 0.15, "logo_opacity": 0.9,
                "replace_audio": True, "bgm_select": "", "bgm_volume": 0.8, "original_volume": 0.0}}
    }
    
    def __init__(self, raw_dir="videos/raw", edited_dir="output",
                 assets_dir="assets", logos_dir="assets/logos", bgm_dir="assets/bgm"):
        self.raw_dir = Path(raw_dir)
        self.edited_dir = Path(edited_dir)
        self.assets_dir = Path(assets_dir)
        self.logos_dir = Path(logos_dir)
        self.bgm_dir = Path(bgm_dir)
        
        for d in [self.raw_dir, self.edited_dir, self.assets_dir, self.logos_dir, self.bgm_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_info(self, video_path):
        """获取视频信息"""
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,duration,r_frame_rate",
               "-show_entries", "format=duration,size",
               "-of", "json", str(video_path)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            d = json.loads(r.stdout)
            s = d.get("streams", [{}])[0]
            f = d.get("format", {})
            return {
                "width": s.get("width", 0), "height": s.get("height", 0),
                "duration": float(s.get("duration") or f.get("duration", 0)),
                "fps": s.get("r_frame_rate", "30/1"),
                "size_mb": int(f.get("size", 0)) / 1024 / 1024
            }
        except:
            return {"width": 0, "height": 0, "duration": 0, "fps": "30/1", "size_mb": 0}
    
    def list_logos(self):
        """列出所有 Logo"""
        logos = []
        if self.logos_dir.exists():
            for f in self.logos_dir.glob("*.png"):
                logos.append({"name": f.name, "path": str(f)})
        return logos
    
    def list_bgms(self):
        """列出所有 BGM"""
        bgms = []
        if self.bgm_dir.exists():
            for f in self.bgm_dir.glob("*"):
                if f.suffix.lower() in [".mp3", ".m4a", ".wav"]:
                    bgms.append({"name": f.name, "path": str(f), "size_mb": round(f.stat().st_size/1024/1024, 2)})
        return bgms
    
    def run_ffmpeg(self, cmd):
        """运行 FFmpeg"""
        try:
            print(f"   FFmpeg: {' '.join(cmd[:8])}...")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                print(f"❌ FFmpeg 错误: {r.stderr[:500]}")
                return False
            return True
        except Exception as e:
            print(f"❌ FFmpeg 异常: {e}")
            return False
    
    def edit_video(self, video_path, config):
        """
        剪辑视频 - 单步处理，9:16 比例
        """
        video_path = Path(video_path)
        note_id = video_path.stem
        output = self.edited_dir / f"edited_{note_id}.mp4"
        
        info = self.get_info(video_path)
        duration = info["duration"]
        w, h = info["width"], info["height"]
        
        if duration <= 0:
            print("❌ 无效视频")
            return None
        
        # 参数
        crop_start = config.get("crop_top", 0)
        crop_end = config.get("crop_bottom", 0)
        speed = config.get("speed", 1.0)
        new_duration = (duration - crop_start - crop_end) / speed
        
        if new_duration <= 0:
            print("❌ 视频太短")
            return None
        
        # Logo 和 BGM 选择
        logo_name = config.get("logo_select", "")
        logo_path = self.logos_dir / logo_name if logo_name else None
        use_logo = config.get("add_logo", False) and logo_path and logo_path.exists()
        
        bgm_name = config.get("bgm_select", "")
        bgm_path = self.bgm_dir / bgm_name if bgm_name else None
        if not bgm_path or not bgm_path.exists():
            bgms = self.list_bgms()
            if bgms:
                bgm_path = Path(bgms[0]["path"])
        
        use_bgm = config.get("replace_audio", False) and bgm_path and bgm_path.exists()
        original_volume = config.get("original_volume", 1.0 if not use_bgm else 0.0)
        
        print(f"\n🎬 剪辑: {note_id}")
        print(f"   输入: {w}x{h} | {duration:.1f}s")
        print(f"   输出: 1080x1920 (9:16) | {new_duration:.1f}s")
        
        # 目标输出尺寸 9:16 = 1080x1920
        target_width = 1080
        target_height = 1920
        
        # ====== 构建 FFmpeg 命令 ======
        # 使用 -ss 和 -t 而不是 trim 滤镜，避免首帧冻结
        
        inputs = ["-i", str(video_path)]
        input_idx = 1
        
        # Logo 输入
        if use_logo:
            inputs.extend(["-i", str(logo_path)])
            print(f"   Logo: {logo_path.name}")
            logo_idx = input_idx
            input_idx += 1
        
        # BGM 输入
        if use_bgm:
            inputs.extend(["-i", str(bgm_path)])
            print(f"   BGM: {bgm_path.name}")
            bgm_idx = input_idx
            input_idx += 1
        
        # 构建视频滤镜
        vf_parts = []
        
        # 1. 水平镜像
        if config.get("hflip", False):
            vf_parts.append("hflip")
        
        # 2. 缩放
        zoom = config.get("zoom", 1.0)
        if zoom != 1.0:
            vf_parts.append(f"scale=iw*{zoom}:ih*{zoom}")
        
        # 3. 裁剪为 9:16 比例（居中裁剪）
        target_ratio = 9/16  # 0.5625
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            # 太宽了，裁剪两边
            new_w = int(h * target_ratio * zoom)
            off = (int(w * zoom) - new_w) // 2
            vf_parts.append(f"crop={new_w}:ih:{off}:0")
        else:
            # 太高了，裁剪上下
            new_h = int(w / target_ratio * zoom)
            off = (int(h * zoom) - new_h) // 2
            vf_parts.append(f"crop=iw:{new_h}:0:{off}")
        
        # 4. 调色
        b, c, s = config.get("brightness", 0), config.get("contrast", 0), config.get("saturation", 0)
        if b or c or s:
            vf_parts.append(f"eq=brightness={b}:contrast={1+c}:saturation={1+s}")
        
        # 5. 最终缩放到 1080x1920
        vf_parts.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black")
        
        # 6. 调速（放在最后）
        if speed != 1.0:
            vf_parts.append(f"setpts=PTS/{speed}")
        
        # 构建 filter_complex
        filter_chains = []
        base_vf = ",".join(vf_parts)
        
        if use_logo:
            ls = config.get("logo_size", 0.12)
            op = config.get("logo_opacity", 0.85)
            pos = config.get("logo_position", "bottom_right")
            lw = int(target_width * ls)
            m = 30
            
            pos_map = {
                "bottom_right": (f"W-w-{m}", f"H-h-{m}"),
                "bottom_left": (str(m), f"H-h-{m}"),
                "top_right": (f"W-w-{m}", str(m)),
                "top_left": (str(m), str(m)),
                "bottom_center": ("(W-w)/2", f"H-h-{m}")
            }
            x, y = pos_map.get(pos, pos_map["bottom_right"])
            
            # Logo 链
            filter_chains.append(f"[{logo_idx}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={op}[logo]")
            # 主视频链
            filter_chains.append(f"[0:v]{base_vf}[v]")
            # 叠加
            filter_chains.append(f"[v][logo]overlay={x}:{y}[outv]")
            video_out = "[outv]"
        else:
            filter_chains.append(f"[0:v]{base_vf}[v]")
            video_out = "[v]"
        
        # 音频处理
        if use_bgm:
            bgm_vol = config.get("bgm_volume", 0.8)
            # BGM 裁剪到精确时长
            filter_chains.append(f"[{bgm_idx}:a]atrim=0:{new_duration},asetpts=PTS-STARTPTS,volume={bgm_vol}[bgm]")
            audio_out = "[bgm]"
        else:
            # 原声调速和音量调整
            if speed != 1.0 and speed <= 2.0:
                filter_chains.append(f"[0:a]atempo={speed},volume={original_volume}[a]")
            else:
                filter_chains.append(f"[0:a]volume={original_volume}[a]")
            audio_out = "[a]"
        
        filter_complex = ";".join(filter_chains)
        
        # 构建完整命令 - 使用 -ss 和 -t 代替 trim 滤镜
        cmd = ["ffmpeg", "-y"]
        
        # 输入和裁剪参数
        cmd.extend(["-ss", str(crop_start)])  # 开始时间
        cmd.extend(["-t", str(duration - crop_start - crop_end)])  # 持续时间
        cmd.extend(inputs)
        
        # 滤镜和输出
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", video_out,
            "-map", audio_out,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-r", "30",  # 强制 30fps，避免帧率问题
            "-movflags", "+faststart",
            str(output)
        ])
        
        if self.run_ffmpeg(cmd):
            out_info = self.get_info(output)
            print(f"✅ 完成: {output.name} ({out_info['size_mb']:.1f}MB, {out_info['duration']:.1f}s)")
            return output
        
        return None


if __name__ == "__main__":
    import sys
    editor = AdvancedVideoEditor()
    
    if len(sys.argv) > 1:
        cfg = {
            "crop_top": 2, "crop_bottom": 2, "speed": 1.2,
            "hflip": True, "zoom": 1.05, "brightness": 0.05,
            "contrast": 0.1, "add_logo": True, 
            "logo_select": "logo_default.png", "logo_position": "bottom_right", "logo_size": 0.12,
            "replace_audio": False, "original_volume": 0.5
        }
        editor.edit_video(sys.argv[1], cfg)
    else:
        print("可用的 Logos:", [l["name"] for l in editor.list_logos()])
        print("可用的 BGM:", [b["name"] for b in editor.list_bgms()])
