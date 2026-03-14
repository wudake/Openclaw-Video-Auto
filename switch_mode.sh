#!/bin/bash
#
# 版本切换脚本
# 用法: ./switch_mode.sh [single|multi]

MODE=${1:-multi}

cd /home/dake/Dake-Video-Auto

if [ "$MODE" == "single" ]; then
    echo "🔄 切换到单用户版本..."
    sed -i 's/app_multi_user.py/app_simple.py/g' start_server.sh
    echo "✅ 已切换到单用户模式"
    echo "   启动文件: start_server.sh"
    echo "   主应用:   app_simple.py"
elif [ "$MODE" == "multi" ]; then
    echo "🔄 切换到多用户版本..."
    sed -i 's/app_simple.py/app_multi_user.py/g' start_server.sh
    echo "✅ 已切换到多用户模式"
    echo "   启动文件: start_server.sh"
    echo "   主应用:   app_multi_user.py"
else
    echo "❌ 用法: $0 [single|multi]"
    echo "   single - 单用户模式"
    echo "   multi  - 多用户模式(默认)"
    exit 1
fi

echo ""
echo "📋 当前配置:"
grep "python.*app_" start_server.sh
echo ""
echo "📝 重启服务生效:"
echo "   ps aux | grep app_ | awk '{print \$2}' | xargs kill -9"
echo "   ./start_server.sh"
