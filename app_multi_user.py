"""
Dake-Video-Auto - 多用户版本 (带任务队列)
支持3人团队同时使用，目录隔离，任务队列调度
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import subprocess
import sys
import json
import secrets
from pathlib import Path
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
# 生成随机密钥用于 Session
app.secret_key = secrets.token_hex(32)

BASE_DIR = Path(__file__).parent

# 添加路径
sys.path.insert(0, str(BASE_DIR / "core"))

# 导入任务队列
from task_queue import TaskQueue, TaskType, TaskStatus

# 初始化任务队列
task_queue = TaskQueue()

# ========== 用户配置 ==========
USERS = {
    "user_a": {"password": "pass_a", "name": "用户 A"},
    "user_b": {"password": "pass_b", "name": "用户 B"},
    "user_c": {"password": "pass_c", "name": "用户 C"},
}

# ========== 登录验证装饰器 ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_dir(user_id):
    """获取用户工作目录"""
    return BASE_DIR / "users" / user_id

def get_user_paths(user_id):
    """获取用户各目录路径"""
    user_dir = get_user_dir(user_id)
    return {
        "base": user_dir,
        "videos_raw": user_dir / "videos" / "raw",
        "videos_configs": user_dir / "videos" / "configs",
        "output": user_dir / "output",
    }

# ========== 路由 ==========

@app.route("/")
def index():
    """首页 - 检查登录状态"""
    if 'user_id' in session:
        return redirect(url_for('app_page'))
    return redirect(url_for('login_page'))

@app.route("/login")
def login_page():
    """登录页面"""
    if 'user_id' in session:
        return redirect(url_for('app_page'))
    return render_template("auth/login.html")

@app.route("/app")
@login_required
def app_page():
    """主应用页面"""
    return render_template("index.html", 
                          user_name=USERS[session['user_id']]['name'],
                          user_id=session['user_id'])

@app.route("/api/login", methods=["POST"])
def login():
    """登录 API"""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if username in USERS and USERS[username]["password"] == password:
        session['user_id'] = username
        return jsonify({"success": True, "user_name": USERS[username]["name"]})
    
    return jsonify({"success": False, "error": "用户名或密码错误"})

@app.route("/api/logout", methods=["POST"])
def logout():
    """登出 API"""
    session.pop('user_id', None)
    return jsonify({"success": True})

@app.route("/api/user/info")
@login_required
def user_info():
    """获取当前用户信息"""
    return jsonify({
        "success": True,
        "user_id": session['user_id'],
        "user_name": USERS[session['user_id']]['name']
    })

# ========== Logo/BGM API (共用素材) ==========

@app.route("/api/logos/list")
@login_required
def list_logos():
    logos_dir = BASE_DIR / "assets" / "logos"
    logos = []
    if logos_dir.exists():
        for f in logos_dir.glob("*.png"):
            logos.append({"name": f.name, "size_kb": round(f.stat().st_size/1024, 1)})
    return jsonify({"logos": logos})

@app.route("/api/bgm/list")
@login_required
def list_bgm():
    bgm_dir = BASE_DIR / "assets" / "bgm"
    bgms = []
    if bgm_dir.exists():
        for f in bgm_dir.glob("*"):
            if f.suffix.lower() in [".mp3", ".m4a", ".wav"]:
                bgms.append({"name": f.name, "size_mb": round(f.stat().st_size/1024/1024, 2)})
    return jsonify({"bgms": bgms})

# ========== 视频下载 API (使用任务队列) ==========

@app.route("/api/download", methods=["POST"])
@login_required
def download_video():
    data = request.json
    url = data.get("url", "").strip()
    user_id = session['user_id']
    
    if not url:
        return jsonify({"success": False, "error": "URL 不能为空"})
    
    # 使用任务队列
    task = task_queue.submit(
        TaskType.DOWNLOAD, 
        user_id, 
        {"url": url},
        priority=0
    )
    
    return jsonify({
        "success": True,
        "task_id": task.task_id,
        "status": task.status.value,
        "message": "任务已加入队列"
    })

# ========== 视频剪辑 API (使用任务队列) ==========

@app.route("/api/edit", methods=["POST"])
@login_required
def edit_video():
    data = request.json
    note_id = data.get("note_id")
    config = data.get("config", {})
    user_id = session['user_id']
    
    if not note_id:
        return jsonify({"success": False, "error": "未指定视频"})
    
    # 使用任务队列
    task = task_queue.submit(
        TaskType.EDIT,
        user_id,
        {"note_id": note_id, "config": config},
        priority=0
    )
    
    return jsonify({
        "success": True,
        "task_id": task.task_id,
        "status": task.status.value,
        "message": "剪辑任务已加入队列"
    })

# ========== 文件上传 API ==========

@app.route("/api/upload/logo", methods=["POST"])
@login_required
def upload_logo():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有文件"})
    file = request.files["file"]
    if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        logos_dir = BASE_DIR / "assets" / "logos"
        logos_dir.mkdir(exist_ok=True)
        file.save(logos_dir / secure_filename(file.filename))
        return jsonify({"success": True, "message": "Logo 上传成功"})
    return jsonify({"success": False, "error": "仅支持 PNG/JPG"})

@app.route("/api/upload/bgm", methods=["POST"])
@login_required
def upload_bgm():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有文件"})
    file = request.files["file"]
    if file.filename.lower().endswith((".mp3", ".m4a", ".wav")):
        bgm_dir = BASE_DIR / "assets" / "bgm"
        bgm_dir.mkdir(exist_ok=True)
        file.save(bgm_dir / secure_filename(file.filename))
        return jsonify({"success": True, "message": "BGM 上传成功"})
    return jsonify({"success": False, "error": "仅支持 MP3/M4A/WAV"})

# ========== 文件下载/预览 API ==========

@app.route("/api/download/edited/<filename>")
@login_required
def download_edited(filename):
    user_id = session['user_id']
    user_paths = get_user_paths(user_id)
    return send_from_directory(user_paths['output'], filename, as_attachment=True)

@app.route("/api/preview/<filename>")
@login_required
def preview_video(filename):
    user_id = session['user_id']
    user_paths = get_user_paths(user_id)
    return send_from_directory(user_paths['output'], filename)

# ========== 用户文件管理 API ==========

@app.route("/api/user/videos")
@login_required
def list_user_videos():
    """列出用户的所有视频"""
    user_id = session['user_id']
    user_paths = get_user_paths(user_id)
    
    videos = []
    if user_paths['output'].exists():
        for f in user_paths['output'].glob("*.mp4"):
            videos.append({
                "name": f.name,
                "size_mb": round(f.stat().st_size/1024/1024, 2),
                "created": f.stat().st_mtime
            })
    
    videos.sort(key=lambda x: x['created'], reverse=True)
    return jsonify({"videos": videos})

# ========== 发布平台 API ==========

@app.route("/api/publish/accounts", methods=["GET"])
@login_required
def get_publish_accounts():
    """获取已配置的发布平台账号"""
    user_id = session['user_id']
    config_file = get_user_paths(user_id)['base'] / "config" / "publish_accounts.json"
    
    accounts = []
    if config_file.exists():
        with open(config_file, 'r') as f:
            data = json.load(f)
            for acc in data:
                accounts.append({
                    "platform": acc["platform"],
                    "username": acc["username"],
                })
    return jsonify({"accounts": accounts})


@app.route("/api/publish/accounts", methods=["POST"])
@login_required
def add_publish_account():
    """添加发布平台账号"""
    user_id = session['user_id']
    data = request.json
    platform = data.get("platform")
    username = data.get("username")
    password = data.get("password")
    
    if not all([platform, username, password]):
        return jsonify({"success": False, "error": "缺少必要参数"})
    
    user_paths = get_user_paths(user_id)
    config_file = user_paths['base'] / "config" / "publish_accounts.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    accounts = []
    if config_file.exists():
        with open(config_file, 'r') as f:
            accounts = json.load(f)
    
    found = False
    for acc in accounts:
        if acc["platform"] == platform:
            acc["username"] = username
            acc["password"] = password
            found = True
            break
    
    if not found:
        accounts.append({
            "platform": platform,
            "username": username,
            "password": password,
            "session_file": ""
        })
    
    with open(config_file, 'w') as f:
        json.dump(accounts, f, indent=2)
    
    return jsonify({"success": True, "message": f"{platform} 账号已保存"})


@app.route("/api/publish", methods=["POST"])
@login_required
def publish_video():
    """发布视频到平台 (使用任务队列)"""
    user_id = session['user_id']
    data = request.json
    video_name = data.get("video_name")
    platforms = data.get("platforms", [])
    caption = data.get("caption", "")
    hashtags = data.get("hashtags", [])
    
    if not video_name:
        return jsonify({"success": False, "error": "未指定视频"})
    
    if not platforms:
        return jsonify({"success": False, "error": "未选择平台"})
    
    user_paths = get_user_paths(user_id)
    video_path = user_paths['output'] / video_name
    
    if not video_path.exists():
        return jsonify({"success": False, "error": "视频文件不存在"})
    
    # 使用任务队列
    task = task_queue.submit(
        TaskType.PUBLISH,
        user_id,
        {
            "video_path": str(video_path),
            "platforms": platforms,
            "caption": caption,
            "hashtags": hashtags
        },
        priority=0
    )
    
    return jsonify({
        "success": True,
        "task_id": task.task_id,
        "status": task.status.value,
        "message": "发布任务已加入队列"
    })


@app.route("/api/logs/publish")
@login_required
def get_publish_logs():
    """获取发布日志"""
    user_id = session['user_id']
    log_file = get_user_paths(user_id)['base'] / "logs" / "publish.log"
    
    if log_file.exists():
        logs = log_file.read_text(encoding='utf-8').split('\n')
        logs = [l for l in logs if l.strip()]
        return jsonify({"logs": logs})
    return jsonify({"logs": []})


@app.route("/api/publish/assistant", methods=["POST"])
@login_required
def publish_assistant():
    """发布助手 - 生成各平台发布信息"""
    from core.publish_assistant import PublishAssistant
    
    user_id = session['user_id']
    data = request.json
    video_name = data.get("video_name")
    caption = data.get("caption", "")
    hashtags = data.get("hashtags", [])
    
    if not video_name:
        return jsonify({"success": False, "error": "未指定视频"})
    
    user_paths = get_user_paths(user_id)
    video_path = user_paths['output'] / video_name
    
    if not video_path.exists():
        return jsonify({"success": False, "error": "视频文件不存在"})
    
    try:
        platforms = PublishAssistant.get_platform_links(
            str(video_path), caption, hashtags
        )
        
        share_info = PublishAssistant.get_shareable_links(
            str(video_path), caption
        )
        
        return jsonify({
            "success": True,
            "data": {
                "video_name": video_name,
                "video_url": f"/api/preview/{video_name}",
                "download_url": f"/api/download/edited/{video_name}",
                "caption": caption,
                "hashtags": hashtags,
                "copy_text": PublishAssistant.generate_caption(caption, hashtags),
                "platforms": platforms,
                "share_info": share_info
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ========== 任务队列 API ==========

@app.route("/api/tasks/submit", methods=["POST"])
@login_required
def submit_task():
    """提交任务"""
    user_id = session['user_id']
    data = request.json
    task_type_str = data.get("task_type")
    params = data.get("params", {})
    priority = data.get("priority", 0)
    
    try:
        task_type = TaskType(task_type_str)
    except ValueError:
        return jsonify({"success": False, "error": "未知任务类型"})
    
    task = task_queue.submit(task_type, user_id, params, priority)
    
    return jsonify({
        "success": True,
        "task_id": task.task_id,
        "status": task.status.value
    })


@app.route("/api/tasks/<task_id>")
@login_required
def get_task_status(task_id):
    """获取任务状态"""
    user_id = session['user_id']
    task = task_queue.get_task(task_id)
    
    if not task or task.user_id != user_id:
        return jsonify({"success": False, "error": "任务不存在"})
    
    return jsonify({
        "success": True,
        "task": task.to_dict()
    })


@app.route("/api/tasks/my")
@login_required
def get_my_tasks():
    """获取当前用户的任务列表"""
    user_id = session['user_id']
    limit = request.args.get("limit", 20, type=int)
    tasks = task_queue.get_user_tasks(user_id, limit)
    
    return jsonify({
        "success": True,
        "tasks": [t.to_dict() for t in tasks]
    })


@app.route("/api/tasks/cancel/<task_id>", methods=["POST"])
@login_required
def cancel_task(task_id):
    """取消任务"""
    user_id = session['user_id']
    success = task_queue.cancel_task(task_id, user_id)
    
    return jsonify({
        "success": success,
        "message": "任务已取消" if success else "无法取消任务"
    })


@app.route("/api/queue/status")
@login_required
def get_queue_status():
    """获取队列状态"""
    status = task_queue.get_queue_status()
    return jsonify({
        "success": True,
        "status": status
    })


if __name__ == "__main__":
    import os
    
    # 确保用户目录存在
    for user_id in USERS.keys():
        paths = get_user_paths(user_id)
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    print("🚀 启动多用户服务: http://172.20.5.151:5000")
    print("👥 支持用户: user_a, user_b, user_c")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
