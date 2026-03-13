"""
发布助手 - 手动辅助发布
生成各平台的发布链接和文案
"""
from pathlib import Path
from typing import List, Dict
import urllib.parse


class PublishAssistant:
    """发布助手 - 生成平台发布链接"""
    
    PLATFORMS = {
        "instagram": {
            "name": "Instagram",
            "icon": "📷",
            "color": "#E4405F",
            "upload_url": "https://www.instagram.com/",
            "description": "网页版不支持上传，请使用手机 App"
        },
        "tiktok": {
            "name": "TikTok",
            "icon": "🎵",
            "color": "#000000",
            "upload_url": "https://www.tiktok.com/upload",
            "description": "点击打开网页版上传页面"
        },
        "youtube": {
            "name": "YouTube Shorts",
            "icon": "▶️",
            "color": "#FF0000",
            "upload_url": "https://studio.youtube.com/video/shorts",
            "description": "点击打开 YouTube Studio"
        },
        "facebook": {
            "name": "Facebook",
            "icon": "📘",
            "color": "#1877F2",
            "upload_url": "https://www.facebook.com/reels/create",
            "description": "点击打开 Reels 创建页面"
        }
    }
    
    @staticmethod
    def generate_caption(title: str, hashtags: List[str]) -> str:
        """生成完整文案"""
        hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
        return f"{title}\n\n{hashtag_str}" if hashtags else title
    
    @staticmethod
    def get_platform_links(video_path: str, title: str, hashtags: List[str]) -> List[Dict]:
        """
        获取各平台的发布链接和信息
        
        Returns:
            [
                {
                    "platform": "instagram",
                    "name": "Instagram",
                    "icon": "📷",
                    "upload_url": "...",
                    "copy_text": "标题和标签文案",
                    "description": "操作说明"
                }
            ]
        """
        copy_text = PublishAssistant.generate_caption(title, hashtags)
        video_name = Path(video_path).name
        
        links = []
        for platform_id, info in PublishAssistant.PLATFORMS.items():
            links.append({
                "platform": platform_id,
                "name": info["name"],
                "icon": info["icon"],
                "color": info["color"],
                "upload_url": info["upload_url"],
                "copy_text": copy_text,
                "description": info["description"],
                "video_name": video_name
            })
        
        return links
    
    @staticmethod
    def get_shareable_links(video_path: str, title: str) -> Dict:
        """生成可分享的链接（用于传输到手机）"""
        # 这里可以集成云存储或本地网络共享
        # 简单返回文件路径信息
        return {
            "local_path": str(video_path),
            "file_name": Path(video_path).name,
            "title": title
        }


if __name__ == "__main__":
    # 测试
    assistant = PublishAssistant()
    links = assistant.get_platform_links(
        "/path/to/video.mp4",
        "Check out our CNC machining process!",
        ["cnc", "machining", "manufacturing", "factory"]
    )
    
    for link in links:
        print(f"\n{link['icon']} {link['name']}")
        print(f"   链接: {link['upload_url']}")
        print(f"   复制: {link['copy_text'][:50]}...")
