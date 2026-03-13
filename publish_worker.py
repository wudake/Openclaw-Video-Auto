#!/usr/bin/env python3
"""
发布工作进程 - 带详细日志
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "core")

# 日志文件
LOG_FILE = Path(__file__).parent / "logs" / "publish.log"
LOG_FILE.parent.mkdir(exist_ok=True)

def log(msg):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def main():
    base_dir = Path(__file__).parent
    
    # 清空旧日志
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    
    log("="*50)
    log("开始发布任务")
    log("="*50)
    
    # 读取发布数据
    temp_file = base_dir / ".temp_publish.json"
    if not temp_file.exists():
        error_msg = "未找到发布数据文件"
        log(f"❌ {error_msg}")
        result = {"success": False, "error": error_msg, "logs": [error_msg]}
        (base_dir / ".temp_publish_result.json").write_text(json.dumps(result))
        return
    
    try:
        data = json.loads(temp_file.read_text(encoding='utf-8'))
        video_path = data["video_path"]
        platforms = data["platforms"]
        caption = data.get("caption", "")
        hashtags = data.get("hashtags", [])
        
        log(f"视频路径: {video_path}")
        log(f"目标平台: {', '.join(platforms)}")
        log(f"标题: {caption[:50]}...")
        log(f"标签: {', '.join(hashtags[:5])}")
        
        # 检查视频文件
        if not Path(video_path).exists():
            error_msg = f"视频文件不存在: {video_path}"
            log(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg}
            (base_dir / ".temp_publish_result.json").write_text(json.dumps(result))
            return
        
        # 导入发布器
        try:
            from publisher import PublishManager
            log("✅ 发布管理器加载成功")
        except Exception as e:
            error_msg = f"导入发布器失败: {str(e)}"
            log(f"❌ {error_msg}")
            log(traceback.format_exc())
            result = {"success": False, "error": error_msg}
            (base_dir / ".temp_publish_result.json").write_text(json.dumps(result))
            return
        
        # 执行发布
        async def do_publish():
            manager = PublishManager()
            
            # 检查账号配置
            log("\n检查账号配置...")
            for platform in platforms:
                if platform not in manager.accounts:
                    log(f"⚠️  未配置 {platform} 账号")
                else:
                    log(f"✅ {platform} 账号: {manager.accounts[platform].username}")
            
            log("\n开始发布...")
            results = await manager.publish(video_path, platforms, caption, hashtags)
            
            # 整理结果
            platform_results = []
            for r in results:
                status = "✅ 成功" if r.success else "❌ 失败"
                log(f"{status} - {r.platform}: {r.url if r.success else r.error}")
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
        log("\n" + "="*50)
        log("发布任务完成")
        log("="*50)
        
    except Exception as e:
        error_msg = f"发布异常: {str(e)}"
        log(f"❌ {error_msg}")
        log(traceback.format_exc())
        result = {"success": False, "error": error_msg}
    
    # 保存结果
    (base_dir / ".temp_publish_result.json").write_text(
        json.dumps(result, ensure_ascii=False),
        encoding='utf-8'
    )
    
    # 清理临时文件
    temp_file.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
