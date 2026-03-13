"""
XHS2IG 主程序
"""
import sys
import yaml
from pathlib import Path
from core.task_queue import PublishQueue
from core.downloader import download_xhs_video
from core.editor import edit_single_video
from core.uploader import IGUploader


def load_config():
    """加载配置文件"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("❌ 配置文件不存在，请复制 config.example.yaml 为 config.yaml 并修改")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def add_video(url):
    """添加视频到队列"""
    print(f"📝 添加视频: {url}")
    
    # 下载（目前需要手动处理）
    result = download_xhs_video(url)
    
    if result and result.get("expected_path"):
        # 添加到队列
        queue = PublishQueue()
        config = load_config()
        caption = config.get("publish", {}).get("caption_template", "")
        
        task = queue.add(
            video_path=result["expected_path"],
            url=url,
            caption=caption
        )
        print(f"\n📋 任务已创建，ID: {task['id']}")
        print(f"⚠️  请手动下载视频到: {result['expected_path']}")
        print("   然后运行: python main.py process")


def batch_add(urls_file):
    """批量添加"""
    path = Path(urls_file)
    if not path.exists():
        print(f"❌ 文件不存在: {urls_file}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📥 批量添加 {len(urls)} 个视频...")
    for url in urls:
        add_video(url)


def process_queue():
    """处理队列：剪辑待处理的视频"""
    config = load_config()
    queue = PublishQueue()
    
    # 扫描 raw 目录
    raw_dir = Path("videos/raw")
    edited_dir = Path("videos/edited")
    
    for video_file in raw_dir.glob("*.mp4"):
        edited_path = edited_dir / f"edited_{video_file.stem}.mp4"
        
        if edited_path.exists():
            print(f"⏭️  已剪辑: {video_file.name}")
            continue
        
        print(f"🎬 剪辑: {video_file.name}")
        result = edit_single_video(video_file, config.get("editing"))
        if result:
            # 更新队列中的视频路径
            for task in queue.queue["pending"]:
                if task["video_path"] == str(video_file):
                    task["edited_path"] = result
                    queue._save()


def publish_next():
    """发布队列中的下一个视频"""
    config = load_config()
    queue = PublishQueue()
    
    task = queue.get_next()
    if not task:
        print("📭 队列为空，没有待发布视频")
        return
    
    # 检查是否有剪辑后的视频
    video_path = task.get("edited_path")
    if not video_path:
        # 尝试找原始视频
        raw_path = Path(task["video_path"])
        edited_path = Path("videos/edited") / f"edited_{raw_path.stem}.mp4"
        if edited_path.exists():
            video_path = str(edited_path)
        elif raw_path.exists():
            video_path = str(raw_path)
        else:
            print(f"❌ 视频文件不存在: {raw_path}")
            queue.mark_failed(task["id"], "视频文件不存在")
            return
    
    # 发布
    ig_config = config.get("instagram", {})
    hashtags = config.get("publish", {}).get("hashtags", [])
    
    try:
        uploader = IGUploader(
            ig_config["username"],
            ig_config["password"]
        )
        
        success = uploader.upload_reel(
            video_path,
            caption=task.get("caption", ""),
            hashtags=hashtags
        )
        
        if success:
            queue.mark_published(task["id"])
            print(f"✅ 任务 {task['id']} 发布完成")
        else:
            queue.mark_failed(task["id"], "发布失败")
            
    except Exception as e:
        print(f"❌ 发布异常: {e}")
        queue.mark_failed(task["id"], str(e))


def show_stats():
    """显示统计"""
    queue = PublishQueue()
    stats = queue.stats()
    print("\n📊 队列统计:")
    print(f"   待发布: {stats['pending']}")
    print(f"   已发布: {stats['published']}")
    print(f"   失败:   {stats['failed']}")


def main():
    if len(sys.argv) < 2:
        print("""
XHS2IG - 小红书 to Instagram 自动化工具

用法:
  python main.py add <url>       添加视频到队列
  python main.py batch <file>    批量添加 (每行一个URL)
  python main.py process         剪辑队列中的视频
  python main.py publish         发布队列中的下一个视频
  python main.py run             一键处理：下载+剪辑+发布 (单个)
  python main.py stats           显示队列统计
""")
        return
    
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) > 2:
        add_video(sys.argv[2])
    elif command == "batch" and len(sys.argv) > 2:
        batch_add(sys.argv[2])
    elif command == "process":
        process_queue()
    elif command == "publish":
        publish_next()
    elif command == "stats":
        show_stats()
    elif command == "run":
        print("🚀 一键处理模式")
        process_queue()
        publish_next()
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
