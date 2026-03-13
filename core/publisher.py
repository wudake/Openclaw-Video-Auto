"""
多平台视频发布模块 - 简化版
支持 Instagram
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    platform: str
    media_id: str = ""
    url: str = ""
    error: str = ""


class PublishManager:
    """发布管理器"""
    
    def __init__(self):
        self.accounts: Dict[str, dict] = {}
        self.load_accounts()
    
    def load_accounts(self):
        """加载已保存的账号"""
        config_file = Path("config/publish_accounts.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)
                for acc_data in data:
                    self.accounts[acc_data["platform"]] = acc_data
    
    async def publish(self, video_path: str, platforms: List[str], 
                     caption: str = "", hashtags: List[str] = None) -> List[PublishResult]:
        """发布到多个平台"""
        if hashtags is None:
            hashtags = []
        
        results = []
        
        for platform in platforms:
            print(f"\n{'='*50}")
            print(f"📱 发布到 {platform.upper()}")
            print('='*50)
            
            if platform not in self.accounts:
                print(f"❌ 未配置 {platform} 账号")
                results.append(PublishResult(False, platform, error="未配置账号"))
                continue
            
            account = self.accounts[platform]
            
            if platform == "instagram":
                # 导入并运行 Instagram 发布器
                try:
                    from core.instagram_publisher import InstagramPublisher
                    publisher = InstagramPublisher(
                        account["username"],
                        account["password"],
                        account.get("session_file", "")
                    )
                    result = publisher.publish(video_path, caption, hashtags)
                    results.append(result)
                except Exception as e:
                    print(f"❌ Instagram 发布异常: {e}")
                    results.append(PublishResult(False, "instagram", error=str(e)))
            else:
                print(f"❌ 暂不支持 {platform}")
                results.append(PublishResult(False, platform, error="暂不支持此平台"))
        
        return results
