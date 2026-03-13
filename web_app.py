"""
XHS2IG Web 界面
Flask 后端 API
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 上传限制

# 项目目录
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 导入核心模块
sys.path.insert(0, str(BASE_DIR / "core"))

# 导入下载器
try:
    from core.downloader_pw import XHSPlaywrightDownloader
    DOWNLOADER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  下载器导入失败: {e}")
    DOWNLOADER_AVAILABLE = False


# ============ API 路由 ============

@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def download_video():
    """下载小红书视频"""
    data = request.json
    url = data.get("url", "").strip()
    
    if not url:
        return jsonify({"success": False, "error": "URL 不能为空"})
    
    if not DOWNLOADER_AVAILABLE:
        return jsonify({"success": False, "error": "下载器未加载"})
    
    try:
        # 创建事件循环运行异步下载
        import asyncio
        
        async def do_download():
            dl = XHSPlaywrightDownloader(raw_dir="videos/raw", headless=True)
            return await dl.download(url)
        
        # 在新的事件循环中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do_download())
        loop.close()
        
        if result and result.get("status") == "success":
            return jsonify({
                "success": True,
                "data": {
                    "note_id": result["note_id"],
                    "video_path": result["output_path"],
                    "size_mb": round(result.get("size_mb", 0), 2),
                    "video_url": result.get("video_url", "")[:100] + "..."
                }
            })
        else:
            error_msg = result.get("error", "下载失败，未找到视频") if result else "下载失败"
            return jsonify({
                "success": False,
                "error": error_msg
            })
    except Exception as e:
        import traceback
        print(f"下载错误: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": f"下载出错: {str(e)}"})


@app.route("/api/videos/raw")
def list_raw_videos():
    """列出所有原始视频"""
    raw_dir = BASE_DIR / "videos" / "raw"
    videos = []
    
    if raw_dir.exists():
        for f in sorted(raw_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            videos.append({
                "name": f.name,
                "note_id": f.stem,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            })
    
    return jsonify({"videos": videos})


@app.route("/api/edit", methods=["POST"])
def edit_video():
    """剪辑视频"""
    data = request.json
    note_id = data.get("note_id")
    config = data.get("config", {})
    
    if not note_id:
        return jsonify({"success": False, "error": "未指定视频"})
    
    try:
        from core.editor_advanced import AdvancedVideoEditor
        
        editor = AdvancedVideoEditor()
        video_path = BASE_DIR / "videos" / "raw" / f"{note_id}.mp4"
        
        if not video_path.exists():
            return jsonify({"success": False, "error": "原始视频不存在"})
        
        result_path = editor.edit_video(video_path, config)
        
        if result_path:
            result_file = Path(result_path)
            stat = result_file.stat()
            return jsonify({
                "success": True,
                "data": {
                    "output_name": result_file.name,
                    "output_path": str(result_path),
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "download_url": f"/api/download/edited/{result_file.name}"
                }
            })
        else:
            return jsonify({"success": False, "error": "剪辑失败，请检查 FFmpeg 是否正常工作"})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": f"剪辑出错: {str(e)}", "detail": traceback.format_exc()})


@app.route("/api/upload/logo", methods=["POST"])
def upload_logo():
    """上传 Logo 文件"""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有文件"})
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名不能为空"})
    
    if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        filename = "logo.png"  # 统一命名为 logo.png
        file.save(BASE_DIR / "assets" / filename)
        return jsonify({"success": True, "message": "Logo 上传成功"})
    
    return jsonify({"success": False, "error": "仅支持 PNG/JPG 格式"})


@app.route("/api/upload/bgm", methods=["POST"])
def upload_bgm():
    """上传 BGM 文件"""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有文件"})
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名不能为空"})
    
    if file and file.filename.lower().endswith((".mp3", ".m4a", ".wav")):
        filename = secure_filename(file.filename)
        bgm_dir = BASE_DIR / "assets" / "bgm"
        bgm_dir.mkdir(exist_ok=True)
        file.save(bgm_dir / filename)
        return jsonify({"success": True, "message": f"BGM {filename} 上传成功"})
    
    return jsonify({"success": False, "error": "仅支持 MP3/M4A/WAV 格式"})


@app.route("/api/bgm/list")
def list_bgm():
    """列出所有 BGM 文件"""
    bgm_dir = BASE_DIR / "assets" / "bgm"
    bgms = []
    
    if bgm_dir.exists():
        for f in bgm_dir.glob("*"):
            if f.suffix.lower() in [".mp3", ".m4a", ".wav"]:
                stat = f.stat()
                bgms.append({
                    "name": f.name,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2)
                })
    
    return jsonify({"bgms": bgms})


@app.route("/api/download/edited/<filename>")
def download_edited(filename):
    """下载剪辑后的视频"""
    output_dir = BASE_DIR / "output"
    return send_from_directory(output_dir, filename, as_attachment=True)


@app.route("/api/preview/<filename>")
def preview_video(filename):
    """预览视频"""
    output_dir = BASE_DIR / "output"
    return send_from_directory(output_dir, filename)


@app.route("/api/output/list")
def list_output():
    """列出所有输出视频"""
    output_dir = BASE_DIR / "output"
    videos = []
    
    if output_dir.exists():
        for f in sorted(output_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            videos.append({
                "name": f.name,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "preview_url": f"/api/preview/{f.name}",
                "download_url": f"/api/download/edited/{f.name}"
            })
    
    return jsonify({"videos": videos})


# 静态文件
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR / "static", filename)


if __name__ == "__main__":
    print("🚀 启动 XHS2IG Web 服务...")
    print("📱 请在浏览器打开: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
