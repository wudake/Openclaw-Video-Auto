#!/usr/bin/env python3
"""
发布工作进程 - 带详细日志 (多用户版本)
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "core")

def get_log_file(user_dir):
    """获取用户日志文件路径"""
    log_file = user_dir / "logs" / "publish.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    return log_file

def log(msg, log_file):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def main():
    base_dir = Path(__file__).parent
    
    # 获取用户ID
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not user_id:
        result = {"success": False, "error": "未指定用户ID"}
        (base_dir / ".temp_publish_result.json").write_text(json.dumps(result))
        return
    
    # 用户目录
    user_dir = base_dir / "users" / user_id
    
    # 日志文件
    LOG_FILE = get_log_file(user_dir)
    
    # 清空旧日志
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    
    log("="*50, LOG_FILE)
    log("开始发布任务", LOG_FILE)
    log("="*50, LOG_FILE)
    
    # 读取发布数据
    temp_file = user_dir / ".temp_publish.json"
    if not temp_file.exists():
        error_msg = "未找到发布数据文件"
        log(f"❌ {error_msg}", LOG_FILE)
        result = {"success": False, "error": error_msg, "logs": [error_msg]}
        (user_dir / ".temp_publish_result.json").write_text(json.dumps(result))
        return
    
    try:
        data = json.loads(temp_file.read_text(encoding='utf-8'))
        video_path = data["video_path"]
        platforms = data["platforms"]
        caption = data.get("caption", "")
        hashtags = data.get("hashtags", [])
        
        log(f"视频路径: {video_path}", LOG_FILE)
        log(f"目标平台: {', '.join(platforms)}", LOG_FILE)
        log(f"标题: {caption[:50]}...", LOG_FILE)
        log(f"标签: {', '.join(hashtags[:5])}", LOG_FILE)
        
        # 检查视频文件
        if not Path(video_path).exists():
            error_msg = f"视频文件不存在: {video_path}"
            log(f"❌ {error_msg}", LOG_FILE)
            result = {"success": False, "error": error_msg}
            (user_dir / ".temp_publish_result.json").write_text(json.dumps(result))
            return
        
        # 导入发布器
        try:
            from publisher import PublishManager
            log("✅ 发布管理器加载成功", LOG_FILE)
        except Exception as e:
            error_msg = f"导入发布器失败: {str(e)}"
            log(f"❌ {error_msg}", LOG_FILE)
            log(traceback.format_exc(), LOG_FILE)
            result = {"success": False, "error": error_msg}
            (user_dir / ".temp_publish_result.json").write_text(json.dumps(result))
            return
        
        # 执行发布
        async def do_publish():
            manager = PublishManager()
            
            # 检查账号配置
            log("\n检查账号配置...", LOG_FILE)
            for platform in platforms:
                if platform not in manager.accounts:
                    log(f"⚠️  未配置 {platform} 账号", LOG_FILE)
                else:
                    log(f"✅ {platform} 账号: {manager.accounts[platform].username}", LOG_FILE)
            
            log("\n开始发布...", LOG_FILE)
            results = await manager.publish(video_path, platforms, caption, hashtags)
            
            # 整理结果
            platform_results = []
            for r in results:
                status = "✅ 成功" if r.success else "❌ 失败"
                log(f"{status} - {r.platform}: {r.url if r.success else r.error}", LOG_FILE)
                platform_results.append({
                    "platform": r.platform,
                    "success": r.success,
                    "url": r.url,
                    "error": r.error
                })
            
            return {
                "success": any(r.success for r in results),
                "results": platform_results
            }
        
        result = asyncio.run(do_publish())
        log("\n" + "="*50, LOG_FILE)
        log("发布任务完成", LOG_FILE)
        log("="*50, LOG_FILE)
        
    except Exception as e:
        error_msg = f"发布异常: {str(e)}"
        log(f"❌ {error_msg}", LOG_FILE)
        log(traceback.format_exc(), LOG_FILE)
        result = {"success": False, "error": error_msg}
    
    # 保存结果到用户目录
    (user_dir / ".temp_publish_result.json").write_text(
        json.dumps(result, ensure_ascii=False),
        encoding='utf-8'
    )
    
    # 清理临时文件
    temp_file.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
