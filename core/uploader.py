"""
Instagram 发布器
使用 instagrapi 库
"""
import os
import json
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired


class IGUploader:
    """Instagram 视频发布器"""
    
    def __init__(self, username, password, session_file="config/ig_session.json"):
        self.username = username
        self.password = password
        self.session_file = Path(session_file)
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.cl = Client()
        self._login()
    
    def _login(self):
        """登录 Instagram"""
        print(f"🔐 登录 Instagram: {self.username}")
        
        # 尝试从 session 文件恢复登录
        if self.session_file.exists():
            try:
                self.cl.load_settings(str(self.session_file))
                self.cl.login(self.username, self.password)
                print("✅ 通过 Session 恢复登录")
                return
            except Exception as e:
                print(f"Session 恢复失败: {e}")
        
        # 重新登录
        try:
            self.cl.login(self.username, self.password)
            self.cl.dump_settings(str(self.session_file))
            print("✅ 登录成功，Session 已保存")
        except ChallengeRequired:
            print("⚠️  需要验证码！请手动登录处理挑战...")
            raise
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            raise
    
    def upload_reel(self, video_path, caption="", hashtags=None):
        """
        发布 Reels 视频
        """
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"❌ 视频文件不存在: {video_path}")
            return False
        
        # 构建 Caption
        if hashtags:
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_str}"
        else:
            full_caption = caption
        
        print(f"📤 正在发布 Reels...")
        print(f"   视频: {video_path.name}")
        print(f"   配文: {caption[:50]}...")
        
        try:
            # 发布视频 (作为 Reels)
            media = self.cl.clip_upload(
                str(video_path),
                caption=full_caption
            )
            print(f"✅ 发布成功! Media ID: {media.pk}")
            return True
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return False
    
    def upload_feed(self, video_path, caption="", hashtags=None):
        """
        发布 Feed 视频
        """
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"❌ 视频文件不存在: {video_path}")
            return False
        
        if hashtags:
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_str}"
        else:
            full_caption = caption
        
        print(f"📤 正在发布 Feed 视频...")
        
        try:
            media = self.cl.video_upload(
                str(video_path),
                caption=full_caption
            )
            print(f"✅ 发布成功! Media ID: {media.pk}")
            return True
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return False


def upload_to_ig(video_path, username, password, caption="", hashtags=None, upload_type="reel"):
    """便捷函数"""
    uploader = IGUploader(username, password)
    
    if upload_type == "reel":
        return uploader.upload_reel(video_path, caption, hashtags)
    else:
        return uploader.upload_feed(video_path, caption, hashtags)


if __name__ == "__main__":
    import sys
    # 测试用
    print("Usage: python uploader.py")
    print("请通过 main.py 或 scheduler.py 调用")
