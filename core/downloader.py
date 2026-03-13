"""
小红书视频下载器
"""
import re
import json
import subprocess
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs


class XHSDownloader:
    """小红书视频下载器"""
    
    def __init__(self, raw_dir="videos/raw"):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_note_id(self, url):
        """从小红书 URL 提取 note ID"""
        # 支持格式：
        # https://www.xiaohongshu.com/explore/65xxxxxx
        # https://xhslink.com/xxxxx
        
        patterns = [
            r'/explore/(\w+)',
            r'/discovery/item/(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 尝试从短链接解析
        if 'xhslink.com' in url:
            import requests
            try:
                resp = requests.head(url, allow_redirects=True, timeout=10)
                final_url = resp.url
                return self.extract_note_id(final_url)
            except Exception as e:
                print(f"短链接解析失败: {e}")
        
        return None
    
    def download(self, url, filename=None):
        """
        下载小红书视频
        使用 yt-dlp 或其他工具
        """
        note_id = self.extract_note_id(url)
        if not note_id:
            print(f"无法解析 URL: {url}")
            return None
        
        if not filename:
            filename = f"{note_id}.mp4"
        
        output_path = self.raw_dir / filename
        
        # 方法1: 尝试使用 yt-dlp (可能不支持小红书)
        # 方法2: 使用专门的解析服务或工具
        
        print(f"正在下载: {url}")
        print(f"Note ID: {note_id}")
        
        # 这里使用一个简单的方法：
        # 实际使用时，你可能需要：
        # 1. 使用油猴脚本获取的视频直链
        # 2. 或者通过移动端 API 抓取
        # 3. 或者使用第三方解析服务
        
        # 临时方案：提示用户手动下载
        print("\n⚠️  注意：小红书反爬严格，建议以下方案：")
        print("1. 使用浏览器扩展（如视频下载助手）手动下载到 videos/raw/")
        print("2. 或使用移动端抓包获取视频直链")
        print("3. 或使用第三方解析 API（需自行寻找稳定服务）")
        print(f"\n请手动下载后重命名为: {filename}")
        print(f"保存路径: {output_path}\n")
        
        return {
            "note_id": note_id,
            "url": url,
            "expected_path": str(output_path),
            "status": "manual_required"
        }


def download_xhs_video(url, output_dir="videos/raw"):
    """便捷函数"""
    dl = XHSDownloader(output_dir)
    return dl.download(url)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = download_xhs_video(url)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python downloader.py <xiaohongshu_url>")
