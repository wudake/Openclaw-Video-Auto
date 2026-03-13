"""
XHS2IG Web 界面 - 修复版
使用子进程方式调用下载器，避免 Playwright 冲突
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def download_video():
    """使用子进程下载视频"""
    data = request.json
    url = data.get("url", "").strip()
    
    if not url:
        return jsonify({"success": False, "error": "URL 不能为空"})
    
    try:
        # 使用子进程运行下载脚本
        cmd = [
            sys.executable, "-c",
            f"""
import asyncio
import sys
sys.path.insert(0, 'core')
from downloader_pw import XHSPlaywrightDownloader

async def download():
    dl = XHSPlaywrightDownloader(raw_dir='videos/raw', headless=True)
    return await dl.download('{url}')

result = asyncio.run(download())
print(json.dumps(result, ensure_ascii=False))
"""
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60,
            cwd=str(BASE_DIR)
        )
        
        # 解析最后一行 JSON 输出
        lines = result.stdout.strip().split('\n')
        json_line = None
        for line in reversed(lines):
            if line.strip().startswith('{'):
                json_line = line
                break
        
        if json_line:
            download_result = json.loads(json_line)
        else:
            return jsonify({"success": False, "error": "下载器无响应"})
        
        if download_result.get("status") == "success":
            return jsonify({
                "success": True,
                "data": {
                    "note_id": download_result["note_id"],
                    "video_path": download_result["output_path"],
                    "size_mb": round(download_result.get("size_mb", 0), 2),
                    "video_url": download_result.get("video_url", "")[:80] + "..."
                }
            })
        else:
            error_msg = download_result.get("error", "下载失败，未找到视频")
            return jsonify({"success": False, "error": error_msg})
            
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "下载超时，请重试"})
    except Exception as e:
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
                "created": __import__('datetime').datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
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
        # 使用子进程运行剪辑
        config_json = json.dumps(config, ensure_ascii=False)
        cmd = [
            sys.executable, "-c",
            f"""
import sys
import json
sys.path.insert(0, 'core')
from editor_advanced import AdvancedVideoEditor

config = json.loads('{config_json}')
editor = AdvancedVideoEditor()
video_path = editor.raw_dir / "{note_id}.mp4"

if not video_path.exists():
    print(json.dumps({{"success": False, "error": "原始视频不存在"}}, ensure_ascii=False))
else:
    result = editor.edit_video(video_path, config)
    if result:
        result_path = str(result)
        print(json.dumps({{
            "success": True, 
            "output_path": result_path,
            "output_name": Path(result_path).name
        }}, ensure_ascii=False))
    else:
        print(json.dumps({{"success": False, "error": "剪辑失败"}}, ensure_ascii=False))
"""
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(BASE_DIR)
        )
        
        # 解析 JSON 输出
        lines = result.stdout.strip().split('\n')
        json_line = None
        for line in reversed(lines):
            if line.strip().startswith('{'):
                json_line = line
                break
        
        if json_line:
            edit_result = json.loads(json_line)
        else:
            return jsonify({"success": False, "error": "剪辑器无响应"})
        
        if edit_result.get("success"):
            output_name = edit_result["output_name"]
            return jsonify({
                "success": True,
                "data": {
                    "output_name": output_name,
                    "output_path": edit_result["output_path"],
                    "preview_url": f"/api/preview/{output_name}",
                    "download_url": f"/api/download/edited/{output_name}"
                }
            })
        else:
            return jsonify({"success": False, "error": edit_result.get("error", "剪辑失败")})
            
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "剪辑超时"})
    except Exception as e:
        return jsonify({"success": False, "error": f"剪辑出错: {str(e)}"})


@app.route("/api/upload/logo", methods=["POST"])
def upload_logo():
    """上传 Logo"""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有文件"})
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名不能为空"})
    
    if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        filename = "logo.png"
        file.save(BASE_DIR / "assets" / filename)
        return jsonify({"success": True, "message": "Logo 上传成功"})
    
    return jsonify({"success": False, "error": "仅支持 PNG/JPG 格式"})


@app.route("/api/upload/bgm", methods=["POST"])
def upload_bgm():
    """上传 BGM"""
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
    """列出所有 BGM"""
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
                "created": __import__('datetime').datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "preview_url": f"/api/preview/{f.name}",
                "download_url": f"/api/download/edited/{f.name}"
            })
    
    return jsonify({"videos": videos})


if __name__ == "__main__":
    print("🚀 启动 XHS2IG Web 服务...")
    print("📱 请在浏览器打开: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
