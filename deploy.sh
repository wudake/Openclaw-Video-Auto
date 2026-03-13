#!/bin/bash
# Dake-Video-Auto 部署脚本

set -e

echo "🚀 开始部署 Dake-Video-Auto..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未安装 Python3"
    exit 1
fi

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "📥 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 安装 Playwright 浏览器
echo "🎭 安装 Playwright Chromium..."
playwright install chromium

# 检查 FFmpeg
echo "🔍 检查 FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  未检测到 FFmpeg，请手动安装:"
    echo "    Ubuntu/Debian: sudo apt install ffmpeg"
    echo "    CentOS/RHEL: sudo yum install ffmpeg"
    exit 1
fi

# 创建必要目录
echo "📁 创建目录结构..."
mkdir -p videos/raw videos/configs output assets/logos assets/bgm config logs

# 检查目录权限
echo "🔒 检查目录权限..."
touch output/.write_test && rm output/.write_test || {
    echo "❌ 无法写入 output 目录，请检查权限"
    exit 1
}

echo ""
echo "✅ 部署完成！"
echo ""
echo "启动服务:"
echo "    ./start_server.sh"
echo ""
echo "或手动启动:"
echo "    source venv/bin/activate"
echo "    python app_simple.py"
echo ""
echo "访问地址: http://<服务器IP>:5000"
