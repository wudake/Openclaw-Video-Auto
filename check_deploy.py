#!/usr/bin/env python3
"""
部署前检查脚本
"""
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 版本过低，需要 3.8+")
        return False
    print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_ffmpeg():
    """检查 FFmpeg"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg: {version}")
            return True
    except FileNotFoundError:
        pass
    print("❌ FFmpeg 未安装")
    return False

def check_directories():
    """检查目录结构"""
    base = Path(__file__).parent
    required_dirs = [
        'videos/raw',
        'videos/configs', 
        'output',
        'assets/logos',
        'assets/bgm',
        'config',
        'logs',
        'core',
        'templates'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        full_path = base / dir_path
        if not full_path.exists():
            print(f"⚠️  目录不存在: {dir_path}")
            all_exist = False
        else:
            print(f"✅ 目录存在: {dir_path}")
    
    return all_exist

def check_core_files():
    """检查核心文件"""
    base = Path(__file__).parent
    required_files = [
        'app_simple.py',
        'requirements.txt',
        'core/downloader_pw.py',
        'core/editor_advanced.py',
        'templates/index.html'
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = base / file_path
        if not full_path.exists():
            print(f"❌ 文件缺失: {file_path}")
            all_exist = False
        else:
            print(f"✅ 文件存在: {file_path}")
    
    return all_exist

def main():
    print("="*50)
    print("🔍 Dake-Video-Auto 部署前检查")
    print("="*50)
    print()
    
    checks = [
        ("Python 版本", check_python_version),
        ("FFmpeg", check_ffmpeg),
        ("目录结构", check_directories),
        ("核心文件", check_core_files)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 检查 {name}...")
        results.append(check_func())
    
    print("\n" + "="*50)
    if all(results):
        print("✅ 所有检查通过，可以部署！")
        print("\n运行部署脚本:")
        print("    ./deploy.sh")
        return 0
    else:
        print("❌ 部分检查未通过，请修复后重试")
        return 1

if __name__ == "__main__":
    sys.exit(main())
