"""
定时调度器
每天 10:00 和 16:00 自动发布
"""
import sys
import yaml
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from main import publish_next, process_queue, load_config


def scheduled_publish():
    """定时发布任务"""
    print(f"\n{'='*50}")
    print(f"⏰ 定时任务触发: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    # 先处理未剪辑的视频
    process_queue()
    
    # 然后发布
    publish_next()
    
    print(f"{'='*50}\n")


def main():
    print("🤖 XHS2IG 定时调度器")
    print("-" * 40)
    
    # 加载配置
    try:
        config = load_config()
    except SystemExit:
        return
    
    # 获取发布时间配置
    scheduler_config = config.get("scheduler", {})
    publish_times = scheduler_config.get("publish_times", ["10:00", "16:00"])
    timezone = scheduler_config.get("timezone", "Asia/Shanghai")
    
    print(f"🌍 时区: {timezone}")
    print(f"📅 发布时间: {', '.join(publish_times)}")
    print("-" * 40)
    
    # 创建调度器
    scheduler = BackgroundScheduler(timezone=timezone)
    
    # 添加定时任务
    for time_str in publish_times:
        try:
            hour, minute = map(int, time_str.split(":"))
            scheduler.add_job(
                scheduled_publish,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=f"publish_{hour}_{minute}",
                replace_existing=True
            )
            print(f"✅ 已设置定时任务: {time_str}")
        except ValueError:
            print(f"❌ 无效的时间格式: {time_str}")
    
    # 启动调度器
    scheduler.start()
    print("-" * 40)
    print("🚀 调度器已启动，按 Ctrl+C 停止\n")
    
    # 保持运行
    try:
        while True:
            import time
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n\n🛑 正在停止调度器...")
        scheduler.shutdown()
        print("✅ 已退出")


if __name__ == "__main__":
    main()
