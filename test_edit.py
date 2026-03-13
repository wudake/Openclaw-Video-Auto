"""
按用户指定配置剪辑视频
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.editor_advanced import AdvancedVideoEditor


# 用户指定的配置
CUSTOM_CONFIG = {
    "preset_key": "custom",
    "preset_name": "用户定制",
    "crop_top": 2,           # 裁剪开头 2 秒
    "crop_bottom": 2,        # 裁剪结尾 2 秒
    "speed": 1.2,            # 调速 1.2x
    "hflip": True,           # 水平镜像翻转
    "zoom": 1.05,            # 缩放 1.05
    "brightness": 0.05,      # 亮度 +5%
    "contrast": 0.1,         # 对比度 +10%
    "saturation": 0.05,      # 饱和度 +5%
    "add_logo": True,        # 添加 Logo
    "logo_position": "bottom_right",  # 右下角
    "logo_size": 0.12,       # Logo 大小 12%
    "logo_opacity": 0.9,     # 透明度 90%
    "replace_audio": True,   # 更换 BGM
    "bgm_volume": 0.8,       # BGM 音量 80%
    "add_subtitle": False
}


def main():
    editor = AdvancedVideoEditor()
    
    # 查找 raw 目录中的视频
    raw_dir = Path("videos/raw")
    videos = list(raw_dir.glob("*.mp4"))
    
    if not videos:
        print("❌ videos/raw/ 目录中没有视频文件")
        print("请先下载视频: python core/downloader_pw.py <小红书链接>")
        return
    
    print(f"📦 发现 {len(videos)} 个视频，开始处理...")
    print("\n🎛️  应用配置:")
    print(f"   ✓ Logo 水印 (右下角)")
    print(f"   ✓ 更换 BGM")
    print(f"   ✓ 水平镜像翻转")
    print(f"   ✓ 裁剪首尾各 2 秒")
    print(f"   ✓ 调速 1.2x")
    print(f"   ✓ 调色 (亮度+5%, 对比度+10%, 饱和度+5%)")
    print(f"   ✓ 缩放 1.05x")
    print("-" * 50)
    
    for video in videos:
        print(f"\n🎬 处理: {video.name}")
        result = editor.edit_video(video, CUSTOM_CONFIG)
        if result:
            print(f"✅ 输出: {result}")
        else:
            print(f"❌ 处理失败")
    
    print("\n" + "="*50)
    print("🎉 全部处理完成！")
    print(f"输出目录: output/")


if __name__ == "__main__":
    main()
