"""
小红书视频下载器 - Playwright 版 (使用系统 Chrome)
"""
import re
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# 系统 Chrome 路径
CHROME_PATH = "/usr/bin/google-chrome"


class XHSPlaywrightDownloader:
    """使用 Playwright + 系统 Chrome 下载小红书视频"""
    
    def __init__(self, raw_dir="videos/raw", headless=True):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
    
    def extract_note_id(self, url):
        """提取笔记 ID"""
        patterns = [
            r'/explore/(\w+)',
            r'/discovery/item/(\w+)',
            r'xhslink\.com/(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def download(self, url, filename=None):
        """下载小红书视频"""
        note_id = self.extract_note_id(url)
        if not note_id:
            print(f"❌ 无法解析 URL: {url}")
            return None
        
        if not filename:
            filename = f"{note_id}.mp4"
        
        output_path = self.raw_dir / filename
        
        print(f"🚀 开始下载: {url}")
        print(f"📌 Note ID: {note_id}")
        
        async with async_playwright() as p:
            # 使用系统 Chrome
            browser = await p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )
            
            page = await context.new_page()
            
            # 存储捕获的视频 URL
            captured_urls = []
            
            # 监听响应
            async def handle_response(response):
                resp_url = response.url
                if '.mp4' in resp_url and ('xiaohongshu' in resp_url or 'xhscdn' in resp_url):
                    if resp_url not in captured_urls:
                        captured_urls.append(resp_url)
                        print(f"🎯 发现视频: {resp_url[:60]}...")
            
            page.on("response", handle_response)
            
            try:
                # 访问页面
                print("⏳ 正在加载页面...")
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # 等待视频加载
                print("⏳ 等待视频加载...")
                await asyncio.sleep(3)
                
                # 尝试点击播放按钮
                try:
                    play_button = await page.query_selector('.play-button, .video-play-btn, [class*="play"]')
                    if play_button:
                        await play_button.click()
                        print("▶️  点击播放按钮")
                        await asyncio.sleep(2)
                except:
                    pass
                
                # 滚动页面触发加载
                await page.evaluate("window.scrollBy(0, 300)")
                await asyncio.sleep(2)
                
                # 查找视频元素
                video_elements = await page.query_selector_all('video')
                print(f"📹 页面发现 {len(video_elements)} 个视频元素")
                
                for i, video in enumerate(video_elements):
                    src = await video.get_attribute('src')
                    if src and src not in captured_urls:
                        captured_urls.append(src)
                        print(f"🎯 视频元素 #{i+1}: {src[:60]}...")
                
                # 从页面源码中提取
                content = await page.content()
                mp4_urls = re.findall(r'https?://[^"\'\s]+\.mp4[^"\'\s]*', content)
                for mp4_url in mp4_urls:
                    if 'xiaohongshu' in mp4_url or 'xhscdn' in mp4_url:
                        clean_url = mp4_url.replace('\\u0026', '&').replace('\\', '')
                        if clean_url not in captured_urls:
                            captured_urls.append(clean_url)
                            print(f"🎯 源码提取: {clean_url[:60]}...")
                
            except PlaywrightTimeout:
                print("❌ 页面加载超时")
            except Exception as e:
                print(f"❌ 页面访问出错: {e}")
            
            await browser.close()
        
        # 下载视频
        if captured_urls:
            # 选择最高质量的
            video_url = captured_urls[0]
            for u in captured_urls:
                if 'hd' in u or u.count('=') > video_url.count('='):
                    video_url = u
            
            print(f"\n📥 开始下载视频...")
            print(f"🔗 URL: {video_url[:80]}...")
            
            import requests
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Referer': 'https://www.xiaohongshu.com/'
                }
                response = requests.get(video_url, headers=headers, stream=True, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                print(f"📦 文件大小: {total_size / 1024 / 1024:.2f} MB")
                
                with open(output_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                
                file_size = output_path.stat().st_size / 1024 / 1024
                print(f"✅ 下载完成: {output_path} ({file_size:.2f} MB)")
                return {
                    "note_id": note_id,
                    "url": url,
                    "video_url": video_url,
                    "output_path": str(output_path),
                    "status": "success",
                    "size_mb": file_size
                }
                
            except Exception as e:
                print(f"❌ 下载失败: {e}")
                return {"note_id": note_id, "url": url, "status": "download_failed", "error": str(e)}
        else:
            print("❌ 未找到视频地址")
            return {"note_id": note_id, "url": url, "status": "no_video_found"}


async def download_xhs_video(url, output_dir="videos/raw", headless=True):
    """便捷函数"""
    dl = XHSPlaywrightDownloader(output_dir, headless)
    return await dl.download(url)


if __name__ == "__main__":
    import sys
    import os
    
    # 检测是否有 DISPLAY 环境变量
    has_display = os.environ.get('DISPLAY') is not None
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        # 没有图形界面时使用 headless 模式
        headless = not has_display
        if headless:
            print("🖥️  无图形界面，使用 headless 模式")
        else:
            print("🖥️  检测到图形界面，显示浏览器窗口")
        
        result = asyncio.run(download_xhs_video(url, headless=headless))
        print("\n" + "="*50)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python downloader_pw.py <xiaohongshu_url>")
