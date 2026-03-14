#!/usr/bin/env python3
"""
下载工作进程 - 支持单用户和多用户模式
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, "core")
from downloader_pw import XHSPlaywrightDownloader

def main():
    base_dir = Path(__file__).parent
    
    # 获取用户ID（单用户模式不传user_id）
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if user_id:
        # 多用户模式
        user_dir = base_dir / "users" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        raw_dir = user_dir / "videos" / "raw"
        url_file = user_dir / ".temp_url.txt"
        result_file = user_dir / ".temp_result.json"
    else:
        # 单用户模式（兼容旧版本）
        raw_dir = base_dir / "videos" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        url_file = base_dir / ".temp_url.txt"
        result_file = base_dir / ".temp_result.json"
    
    # 读取 URL
    if not url_file.exists():
        result = {"status": "error", "error": "未找到 URL 文件"}
        result_file.write_text(json.dumps(result))
        return
    
    url = url_file.read_text(encoding='utf-8').strip()
    
    # 下载
    async def do_download():
        dl = XHSPlaywrightDownloader(raw_dir=str(raw_dir), headless=True)
        return await dl.download(url)
    
    try:
        result = asyncio.run(do_download())
    except Exception as e:
        result = {"status": "error", "error": str(e)}
    
    # 保存结果
    result_file.write_text(
        json.dumps(result, ensure_ascii=False), 
        encoding='utf-8'
    )

if __name__ == "__main__":
    main()
