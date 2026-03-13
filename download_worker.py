#!/usr/bin/env python3
"""
下载工作进程 - 独立脚本
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
    
    # 读取 URL
    url_file = base_dir / ".temp_url.txt"
    if not url_file.exists():
        result = {"status": "error", "error": "未找到 URL 文件"}
        (base_dir / ".temp_result.json").write_text(json.dumps(result))
        return
    
    url = url_file.read_text(encoding='utf-8').strip()
    
    # 下载
    async def do_download():
        dl = XHSPlaywrightDownloader(raw_dir="videos/raw", headless=True)
        return await dl.download(url)
    
    try:
        result = asyncio.run(do_download())
    except Exception as e:
        result = {"status": "error", "error": str(e)}
    
    # 保存结果
    (base_dir / ".temp_result.json").write_text(
        json.dumps(result, ensure_ascii=False), 
        encoding='utf-8'
    )

if __name__ == "__main__":
    main()
