"""
Instagram 发布器 - 修复版
处理验证码和详细日志
"""
import json
import time
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    platform: str
    media_id: str = ""
    url: str = ""
    error: str = ""


class InstagramPublisher:
    """Instagram 发布器 - 修复版"""
    
    def __init__(self, username: str, password: str, session_file: str = ""):
        self.username = username
        self.password = password
        self.session_file = session_file
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            from instagrapi import Client
            self.client = Client()
            
            # 增加请求延迟，减少风控概率
            self.client.delay_range = [2, 5]
            
            # 尝试加载会话
            if self.session_file:
                session_path = Path(self.session_file)
                if session_path.exists():
                    try:
                        self.client.load_settings(str(session_path))
                        print("✅ 已加载保存的会话")
                    except Exception as e:
                        print(f"⚠️  加载会话失败: {e}")
        except ImportError as e:
            print(f"❌ 导入 instagrapi 失败: {e}")
    
    def login(self) -> bool:
        """登录 Instagram，处理验证码"""
        try:
            if not self.client:
                return False
            
            # 先尝试使用现有会话
            if self.session_file and Path(self.session_file).exists():
                try:
                    print("🔐 尝试使用现有会话...")
                    self.client.get_timeline_feed()
                    print("✅ 会话有效，已登录")
                    return True
                except Exception as e:
                    print(f"⚠️  会话失效: {e}")
            
            # 重新登录
            print(f"🔐 登录 Instagram: {self.username}")
            print("   这可能需要一些时间，请耐心等待...")
            
            try:
                self.client.login(self.username, self.password)
            except Exception as login_error:
                error_str = str(login_error)
                
                # 处理验证码
                if "challenge" in error_str.lower() or "checkpoint" in error_str.lower():
                    print("⚠️  Instagram 需要验证码验证")
                    print("   请在前端输入收到的验证码...")
                    # 这里需要前端交互，暂时返回失败
                    return False
                
                raise login_error
            
            # 保存会话
            session_dir = Path("config/sessions")
            session_dir.mkdir(parents=True, exist_ok=True)
            self.session_file = str(session_dir / f"ig_{self.username}.json")
            self.client.dump_settings(self.session_file)
            
            print(f"✅ Instagram 登录成功")
            print(f"   会话已保存: {self.session_file}")
            return True
            
        except Exception as e:
            print(f"❌ Instagram 登录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def publish(self, video_path: str, caption: str, hashtags: List[str]) -> PublishResult:
        """发布到 Instagram Reels"""
        try:
            # 登录
            if not self.login():
                return PublishResult(False, "instagram", error="登录失败")
            
            # 构建完整 caption
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_str}" if hashtags else caption
            
            print(f"📤 开始上传视频到 Instagram...")
            print(f"   视频: {Path(video_path).name}")
            print(f"   标题: {caption[:50]}...")
            print(f"   大小: {Path(video_path).stat().st_size / 1024 / 1024:.1f} MB")
            
            # 上传视频（使用 clip_upload 发布 Reels）
            print("   正在上传... (这可能需要几分钟)")
            start_time = time.time()
            
            try:
                media = self.client.clip_upload(video_path, caption=full_caption)
            except Exception as upload_error:
                print(f"❌ 上传失败: {upload_error}")
                # 检查是否是格式问题
                if "format" in str(upload_error).lower() or "codec" in str(upload_error).lower():
                    return PublishResult(
                        False, "instagram",
                        error="视频格式问题，请确保是 9:16 竖屏 MP4 格式"
                    )
                raise upload_error
            
            elapsed = time.time() - start_time
            print(f"   上传完成，耗时: {elapsed:.1f} 秒")
            
            # 构建 URL
            url = f"https://instagram.com/reel/{media.code}/"
            
            print(f"✅ Instagram 发布成功!")
            print(f"   链接: {url}")
            
            return PublishResult(
                success=True,
                platform="instagram",
                media_id=str(media.pk),
                url=url
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Instagram 发布失败: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # 友好的错误提示
            if "login" in error_msg.lower():
                return PublishResult(False, "instagram", error="登录失败，请检查账号密码")
            elif "ratelimit" in error_msg.lower() or "rate limit" in error_msg.lower():
                return PublishResult(False, "instagram", error="触发频率限制，请稍后再试")
            elif "spam" in error_msg.lower():
                return PublishResult(False, "instagram", error="被标记为垃圾内容，请更换标题或标签")
            else:
                return PublishResult(False, "instagram", error=f"发布失败: {error_msg}")


# 测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 4:
        username = sys.argv[1]
        password = sys.argv[2]
        video_path = sys.argv[3]
        
        publisher = InstagramPublisher(username, password)
        result = publisher.publish(video_path, "Test post", ["test"])
        
        print(f"\n结果: {result}")
    else:
        print("用法: python instagram_publisher.py <username> <password> <video_path>")
