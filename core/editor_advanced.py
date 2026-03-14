"""
高级视频编辑器 - v2.2
添加字幕功能：语音识别、样式配置、自适应大小
"""
import json
import subprocess
import whisper
import re
from pathlib import Path
from datetime import timedelta


class AdvancedVideoEditor:
    """高级视频剪辑器 v2.2 - 支持字幕"""
    
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
    
    # 字幕样式预设
    SUBTITLE_STYLES = {
        "white_black": {
            "name": "白字黑边",
            "font_color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_width": 2,
            "shadow": 1
        },
        "yellow_black": {
            "name": "黄字黑边",
            "font_color": "#FFFF00",
            "outline_color": "#000000",
            "outline_width": 2,
            "shadow": 1
        },
        "white_red": {
            "name": "白字红边",
            "font_color": "#FFFFFF",
            "outline_color": "#FF0000",
            "outline_width": 2,
            "shadow": 1
        },
        "black_white": {
            "name": "黑字白边",
            "font_color": "#000000",
            "outline_color": "#FFFFFF",
            "outline_width": 2,
            "shadow": 1
        },
        "cyan_black": {
            "name": "青字黑边",
            "font_color": "#00FFFF",
            "outline_color": "#000000",
            "outline_width": 2,
            "shadow": 1
        },
        "pink_black": {
            "name": "粉字黑边",
            "font_color": "#FF69B4",
            "outline_color": "#000000",
            "outline_width": 2,
            "shadow": 1
        }
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
        
        # Whisper 模型（延迟加载）
        self._whisper_model = None
    
    def _get_whisper_model(self, model_size="base"):
        """获取 Whisper 模型"""
        if self._whisper_model is None:
            print(f"   加载 Whisper 模型 ({model_size})...")
            self._whisper_model = whisper.load_model(model_size)
        return self._whisper_model
    
    def generate_subtitles(self, video_path, output_srt=None, language="zh", model_size="base"):
        """
        使用 Whisper 生成 SRT 字幕
        
        Args:
            video_path: 视频路径
            output_srt: 输出 SRT 路径，None则自动生成
            language: 语言代码 (zh, en, ja, ko, auto)
            model_size: 模型大小 (tiny, base, small, medium, large)
            
        Returns:
            SRT 文件路径
        """
        video_path = Path(video_path)
        if output_srt is None:
            output_srt = video_path.with_suffix('.srt')
        else:
            output_srt = Path(output_srt)
        
        print(f"\n📝 生成字幕: {video_path.name}")
        
        model = self._get_whisper_model(model_size)
        
        # 转录
        result = model.transcribe(
            str(video_path),
            language=None if language == "auto" else language,
            verbose=False
        )
        
        # 生成 SRT
        srt_lines = []
        for i, segment in enumerate(result["segments"], 1):
            start = self._seconds_to_srt_time(segment["start"])
            end = self._seconds_to_srt_time(segment["end"])
            text = segment["text"].strip()
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")
        
        output_srt.write_text("\n".join(srt_lines), encoding='utf-8')
        print(f"   ✅ 字幕生成: {output_srt.name} ({len(result['segments'])} 句)")
        
        return output_srt
    
    def _seconds_to_srt_time(self, seconds):
        """秒转 SRT 时间格式"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hrs = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"
    
    def calculate_font_size(self, text, video_width=1080, max_font_size=24, min_font_size=16, fixed_size=None):
        """
        根据字幕长度计算自适应字体大小
        
        Args:
            text: 字幕文本
            video_width: 视频宽度
            max_font_size: 最大字体大小 (默认24)
            min_font_size: 最小字体大小 (默认16)
            fixed_size: 固定字体大小 (如果指定则使用固定值)
            
        Returns:
            计算后的字体大小
        """
        # 如果指定了固定大小，直接返回
        if fixed_size is not None:
            return fixed_size
        
        # 按字符数计算
        char_count = len(text)
        
        if char_count <= 10:
            return max_font_size
        elif char_count <= 20:
            return int(max_font_size * 0.9)
        elif char_count <= 30:
            return int(max_font_size * 0.8)
        else:
            return min_font_size
    
    def burn_subtitles(self, video_path, srt_path, output_path, style_config=None):
        """
        将字幕烧录到视频
        
        Args:
            video_path: 输入视频路径
            srt_path: SRT 字幕路径
            output_path: 输出视频路径
            style_config: 样式配置字典
                - style_preset: 预设样式名称
                - font_color: 字体颜色 (#RRGGBB)
                - outline_color: 描边颜色
                - outline_width: 描边宽度
                - font_size: 字体大小 (None则自动计算)
                - position: 位置 (bottom, middle, top)
                - max_width: 最大行宽百分比 (0-1)
        """
        video_path = Path(video_path)
        srt_path = Path(srt_path)
        output_path = Path(output_path)
        
        if style_config is None:
            style_config = {}
        
        print(f"\n🔥 烧录字幕: {srt_path.name}")
        
        # 获取样式
        preset_name = style_config.get("style_preset", "white_black")
        preset = self.SUBTITLE_STYLES.get(preset_name, self.SUBTITLE_STYLES["white_black"])
        
        font_color = style_config.get("font_color", preset["font_color"])
        outline_color = style_config.get("outline_color", preset["outline_color"])
        outline_width = style_config.get("outline_width", preset["outline_width"])
        shadow = style_config.get("shadow", preset["shadow"])
        
        # 字体大小（自动计算或使用指定值，包括固定大小）
        font_size = style_config.get("font_size")
        custom_size = style_config.get("custom_font_size")
        
        if custom_size is not None and custom_size > 0:
            # 使用自定义固定大小
            font_size = int(custom_size)
            print(f"   字体大小: 自定义 {font_size}px")
        elif font_size is None:
            # 读取 SRT 计算平均长度
            srt_content = srt_path.read_text(encoding='utf-8')
            texts = re.findall(r'\n\n(\d+)\n.*?\n(.*?)(?=\n\n|\Z)', srt_content, re.DOTALL)
            if texts:
                avg_length = sum(len(t[1].strip()) for t in texts) / len(texts)
                font_size = self.calculate_font_size("x" * int(avg_length))
            else:
                font_size = 36
            print(f"   字体大小: 自适应 {font_size}px")
        
        # 位置
        position = style_config.get("position", "bottom")
        margin_v = {"top": 50, "middle": 540, "bottom": 100}.get(position, 100)
        
        # 最大行宽
        max_width = style_config.get("max_width", 0.9)
        
        # 构建字幕滤镜参数
        # FFmpeg subtitles 滤镜支持 ASS 样式，我们通过 force_style 传递参数
        font_color_hex = font_color.lstrip('#')
        outline_color_hex = outline_color.lstrip('#')
        
        # 转换颜色格式：#RRGGBB -> &HBBGGRR (ASS 格式)
        def hex_to_ass(hex_color):
            r = hex_color[0:2]
            g = hex_color[2:4]
            b = hex_color[4:6]
            return f"&H{b}{g}{r}"
        
        font_color_ass = hex_to_ass(font_color_hex)
        outline_color_ass = hex_to_ass(outline_color_hex)
        
        # 构建 force_style 字符串
        style_str = (
            f"FontName=Arial,"
            f"FontSize={font_size},"
            f"PrimaryColour={font_color_ass},"
            f"OutlineColour={outline_color_ass},"
            f"Outline={outline_width},"
            f"Shadow={shadow},"
            f"Alignment=2,"  # 底部居中
            f"MarginV={margin_v},"
            f"WrapStyle=0,"
            f"BorderStyle=1"
        )
        
        vf_filter = f"subtitles={srt_path}:force_style='{style_str}'"
        
        # 如果需要限制行宽，使用 wrap 处理
        # 这里我们使用 ASS 的 WrapStyle=0 自动换行
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf_filter,
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        if self.run_ffmpeg(cmd):
            print(f"   ✅ 字幕烧录完成: {output_path.name}")
            return output_path
        return None
    
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
        剪辑视频 - 支持字幕
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
        
        # 字幕配置
        add_subtitles = config.get("add_subtitles", False)
        subtitle_style = config.get("subtitle_style", "white_black")
        subtitle_position = config.get("subtitle_position", "bottom")
        subtitle_font_size = config.get("subtitle_font_size")  # None 表示自动
        subtitle_custom_size = config.get("subtitle_custom_size")  # 自定义固定大小
        
        print(f"\n🎬 剪辑: {note_id}")
        print(f"   输入: {w}x{h} | {duration:.1f}s")
        if crop_start > 0 or crop_end > 0:
            print(f"   裁剪: 头部-{crop_start}s, 尾部-{crop_end}s")
        print(f"   输出: 1080x1920 (9:16) | {new_duration:.1f}s")
        
        target_width = 1080
        target_height = 1920
        
        # ====== 构建 FFmpeg 命令 ======
        inputs = ["-i", str(video_path)]
        input_idx = 1
        
        if use_logo:
            inputs.extend(["-i", str(logo_path)])
            print(f"   Logo: {logo_path.name}")
            logo_idx = input_idx
            input_idx += 1
        
        if use_bgm:
            inputs.extend(["-i", str(bgm_path)])
            print(f"   BGM: {bgm_path.name}")
            bgm_idx = input_idx
            input_idx += 1
        
        # 构建视频滤镜
        vf_parts = []
        
        if config.get("hflip", False):
            vf_parts.append("hflip")
        
        zoom = config.get("zoom", 1.0)
        if zoom != 1.0:
            vf_parts.append(f"scale=iw*{zoom}:ih*{zoom}")
        
        target_ratio = 9/16
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            new_w = int(h * target_ratio * zoom)
            off = (int(w * zoom) - new_w) // 2
            vf_parts.append(f"crop={new_w}:ih:{off}:0")
        else:
            new_h = int(w / target_ratio * zoom)
            off = (int(h * zoom) - new_h) // 2
            vf_parts.append(f"crop=iw:{new_h}:0:{off}")
        
        b, c, s = config.get("brightness", 0), config.get("contrast", 0), config.get("saturation", 0)
        if b or c or s:
            vf_parts.append(f"eq=brightness={b}:contrast={1+c}:saturation={1+s}")
        
        vf_parts.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black")
        
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
            
            filter_chains.append(f"[{logo_idx}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={op}[logo]")
            filter_chains.append(f"[0:v]{base_vf}[v]")
            filter_chains.append(f"[v][logo]overlay={x}:{y}[outv]")
            video_out = "[outv]"
        else:
            filter_chains.append(f"[0:v]{base_vf}[v]")
            video_out = "[v]"
        
        # 音频处理
        if use_bgm:
            bgm_vol = config.get("bgm_volume", 0.8)
            filter_chains.append(f"[{bgm_idx}:a]atrim=0:{new_duration},asetpts=PTS-STARTPTS,volume={bgm_vol}[bgm]")
            audio_out = "[bgm]"
        else:
            if speed != 1.0 and speed <= 2.0:
                filter_chains.append(f"[0:a]atempo={speed},volume={original_volume}[a]")
            else:
                filter_chains.append(f"[0:a]volume={original_volume}[a]")
            audio_out = "[a]"
        
        filter_complex = ";".join(filter_chains)
        
        cmd = ["ffmpeg", "-y"]
        cmd.extend(["-ss", str(crop_start)])
        cmd.extend(["-t", str(duration - crop_start - crop_end)])
        cmd.extend(inputs)
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", video_out,
            "-map", audio_out,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-r", "30",
            "-movflags", "+faststart",
            str(output)
        ])
        
        if self.run_ffmpeg(cmd):
            # 生成并烧录字幕
            if add_subtitles:
                print(f"\n📝 处理字幕...")
                try:
                    # 自定义字幕
                    custom_text = config.get("subtitle_text", "")
                    start_time = config.get("subtitle_start", 0)
                    end_time = config.get("subtitle_end", 5)
                    
                    if custom_text:
                        # 创建自定义 SRT 文件
                        srt_path = self.edited_dir / f"edited_{note_id}.srt"
                        srt_content = f"1\n{self._seconds_to_srt_time(start_time)} --> {self._seconds_to_srt_time(end_time)}\n{custom_text}\n"
                        srt_path.write_text(srt_content, encoding='utf-8')
                        print(f"   自定义字幕: '{custom_text}' ({start_time}s - {end_time}s)")
                        
                        # 样式配置
                        style_cfg = {
                            "style_preset": subtitle_style,
                            "position": subtitle_position,
                            "font_size": subtitle_font_size,
                            "custom_font_size": subtitle_custom_size
                        }
                        
                        # 烧录字幕到新文件
                        final_output = self.edited_dir / f"edited_{note_id}_sub.mp4"
                        result = self.burn_subtitles(output, srt_path, final_output, style_cfg)
                        
                        if result:
                            # 删除无字幕版本，重命名有字幕版本
                            output.unlink()
                            final_output.rename(output)
                            print(f"✅ 字幕添加完成")
                        else:
                            print(f"⚠️ 字幕烧录失败，使用无字幕版本")
                        
                        # 清理 SRT 文件
                        srt_path.unlink(missing_ok=True)
                    else:
                        print("   ⚠️ 未输入字幕内容，跳过")
                    
                except Exception as e:
                    print(f"⚠️ 字幕处理失败: {e}")
            
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
            "replace_audio": False, "original_volume": 0.5,
            "add_subtitles": True,
            "subtitle_style": "white_black",
            "subtitle_position": "bottom"
        }
        editor.edit_video(sys.argv[1], cfg)
    else:
        print("可用的 Logos:", [l["name"] for l in editor.list_logos()])
        print("可用的 BGM:", [b["name"] for b in editor.list_bgms()])
        print("字幕样式:", list(editor.SUBTITLE_STYLES.keys()))
