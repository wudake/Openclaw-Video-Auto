"""
XHS2IG Web API - 简化版
直接调用，避免子进程问题
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

# 添加路径
sys.path.insert(0, str(BASE_DIR / "core"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def download_video():
    """下载小红书视频 - 使用独立脚本文件"""
    data = request.json
    url = data.get("url", "").strip()
    
    if not url:
        return jsonify({"success": False, "error": "URL 不能为空"})
    
    # 保存 URL 到临时文件
    temp_file = BASE_DIR / ".temp_url.txt"
    temp_file.write_text(url, encoding='utf-8')
    
    try:
        # 运行下载脚本
        script_path = BASE_DIR / "download_worker.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(BASE_DIR)
        )
        
        # 读取结果
        result_file = BASE_DIR / ".temp_result.json"
        if result_file.exists():
            download_result = json.loads(result_file.read_text(encoding='utf-8'))
            result_file.unlink()
        else:
            return jsonify({"success": False, "error": "下载器未返回结果"})
        
        temp_file.unlink(missing_ok=True)
        
        if download_result.get("status") == "success":
            return jsonify({
                "success": True,
                "data": {
                    "note_id": download_result["note_id"],
                    "video_path": download_result["output_path"],
                    "size_mb": round(download_result.get("size_mb", 0), 2)
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": download_result.get("error", "下载失败")
            })
            
    except subprocess.TimeoutExpired:
        temp_file.unlink(missing_ok=True)
        return jsonify({"success": False, "error": "下载超时，请重试"})
    except Exception as e:
        temp_file.unlink(missing_ok=True)
        return jsonify({"success": False, "error": f"下载出错: {str(e)}"})


@app.route("/api/edit", methods=["POST"])
def edit_video():
    """剪辑视频"""
    data = request.json
    note_id = data.get("note_id")
    config = data.get("config", {})
    
    if not note_id:
        return jsonify({"success": False, "error": "未指定视频"})
    
    # 保存配置
    temp_config = BASE_DIR / ".temp_config.json"
    temp_config.write_text(json.dumps({"note_id": note_id, "config": config}), encoding='utf-8')
    
    try:
        script_path = BASE_DIR / "edit_worker.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(BASE_DIR)
        )
        
        result_file = BASE_DIR / ".temp_edit_result.json"
        if result_file.exists():
            edit_result = json.loads(result_file.read_text(encoding='utf-8'))
            result_file.unlink()
        else:
            temp_config.unlink(missing_ok=True)
            return jsonify({"success": False, "error": "剪辑器未返回结果"})
        
        temp_config.unlink(missing_ok=True)
        
        if edit_result.get("success"):
            output_name = edit_result["output_name"]
            return jsonify({
                "success": True,
                "data": {
                    "output_name": output_name,
                    "preview_url": f"/api/preview/{output_name}",
                    "download_url": f"/api/download/edited/{output_name}"
                }
            })
        else:
            return jsonify({"success": False, "error": edit_result.get("error", "剪辑失败")})
            
    except subprocess.TimeoutExpired:
        temp_config.unlink(missing_ok=True)
        return jsonify({"success": False, "error": "剪辑超时"})
    except Exception as e:
        temp_config.unlink(missing_ok=True)
        return jsonify({"success": False, "error": f"剪辑出错: {str(e)}"})


@app.route("/api/logos/list")
def list_logos():
    """列出所有 Logo"""
    logos_dir = BASE_DIR / "assets" / "logos"
    logos = []
    if logos_dir.exists():
        for f in logos_dir.glob("*.png"):
            stat = f.stat()
            logos.append({
                "name": f.name,
                "size_kb": round(stat.st_size / 1024, 1)
            })
    return jsonify({"logos": logos})


@app.route("/api/upload/logo", methods=["POST"])
def upload_logo():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有文件"})
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名不能为空"})
    
    if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        filename = secure_filename(file.filename)
        logos_dir = BASE_DIR / "assets" / "logos"
        logos_dir.mkdir(exist_ok=True)
        file.save(logos_dir / filename)
        return jsonify({"success": True, "message": f"Logo {filename} 上传成功"})
    
    return jsonify({"success": False, "error": "仅支持 PNG/JPG 格式"})


@app.route("/api/upload/bgm", methods=["POST"])
def upload_bgm():
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
    bgm_dir = BASE_DIR / "assets" / "bgm"
    bgms = []
    if bgm_dir.exists():
        for f in bgm_dir.glob("*"):
            if f.suffix.lower() in [".mp3", ".m4a", ".wav"]:
                stat = f.stat()
                bgms.append({"name": f.name, "size_mb": round(stat.st_size / 1024 / 1024, 2)})
    return jsonify({"bgms": bgms})


@app.route("/api/download/edited/<filename>")
def download_edited(filename):
    output_dir = BASE_DIR / "output"
    return send_from_directory(output_dir, filename, as_attachment=True)


@app.route("/api/preview/<filename>")
def preview_video(filename):
    output_dir = BASE_DIR / "output"
    return send_from_directory(output_dir, filename)


@app.route("/api/output/list")
def list_output():
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
    print("📱 http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
