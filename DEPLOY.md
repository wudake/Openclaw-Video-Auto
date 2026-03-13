# Dake-Video-Auto 部署指南

## 系统要求

- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 7+)
- **Python**: 3.8+
- **内存**: 至少 2GB RAM
- **磁盘**: 至少 10GB 可用空间

## 必需软件

### 1. Python3 和 pip
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# CentOS/RHEL
sudo yum install python3 python3-pip -y
```

### 2. FFmpeg
```bash
# Ubuntu/Debian
sudo apt install ffmpeg -y

# CentOS/RHEL
sudo yum install ffmpeg -y
```

### 3. 系统依赖 (Playwright 需要)
```bash
# Ubuntu/Debian
sudo apt install libnss3 libatk-bridge2.0-0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 -y

# CentOS/RHEL
sudo yum install nss atk bridge-utils xorg-x11-server-Xvfb -y
```

## 部署步骤

### 方式 1：使用部署脚本

```bash
# 克隆项目
git clone https://github.com/wudake/Openclaw-Video-Auto.git
cd Openclaw-Video-Auto

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 方式 2：手动部署

```bash
# 1. 克隆项目
git clone https://github.com/wudake/Openclaw-Video-Auto.git
cd Openclaw-Video-Auto

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 Playwright 浏览器
playwright install chromium

# 5. 创建目录
mkdir -p videos/raw videos/configs output assets/logos assets/bgm config logs

# 6. 启动服务
./start_server.sh
```

## 配置

### 防火墙设置
```bash
# 开放 5000 端口 (Ubuntu/Debian)
sudo ufw allow 5000/tcp

# 或 CentOS/RHEL
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 使用 Nginx 反向代理 (可选)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/preview {
        proxy_pass http://127.0.0.1:5000;
        proxy_buffering off;
    }
}
```

### Systemd 服务 (推荐用于生产环境)

创建 `/etc/systemd/system/dake-video.service`:

```ini
[Unit]
Description=Dake Video Auto Tool
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Openclaw-Video-Auto
Environment="PATH=/path/to/Openclaw-Video-Auto/venv/bin"
ExecStart=/path/to/Openclaw-Video-Auto/venv/bin/python app_simple.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable dake-video
sudo systemctl start dake-video
sudo systemctl status dake-video
```

## 目录说明

```
Openclaw-Video-Auto/
├── venv/                  # 虚拟环境 (自动创建)
├── videos/
│   ├── raw/              # 原始下载视频
│   └── configs/          # 视频配置
├── output/               # 剪辑后视频输出
├── assets/
│   ├── logos/            # Logo 文件
│   └── bgm/              # BGM 文件
├── config/               # 配置文件
├── logs/                 # 日志文件
├── app_simple.py         # 主应用
├── requirements.txt      # Python 依赖
└── deploy.sh             # 部署脚本
```

## 常见问题

### 1. Playwright 安装失败
```bash
# 安装系统依赖
sudo apt install libnss3 libatk-bridge2.0-0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2

# 重新安装
playwright install chromium
```

### 2. FFmpeg 未找到
```bash
# 检查是否安装
which ffmpeg

# 如果没有，安装它
sudo apt install ffmpeg
```

### 3. 权限问题
```bash
# 确保目录可写
chmod -R 755 output videos assets logs
```

### 4. 端口被占用
```bash
# 查找占用 5000 端口的进程
sudo lsof -i :5000

# 杀死进程
sudo kill -9 <PID>
```

## 更新项目

```bash
cd Openclaw-Video-Auto
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

## 卸载

```bash
cd Openclaw-Video-Auto
sudo systemctl stop dake-video  # 如果使用 systemd
sudo systemctl disable dake-video
rm -rf venv
# 删除项目目录
cd ..
rm -rf Openclaw-Video-Auto
```
