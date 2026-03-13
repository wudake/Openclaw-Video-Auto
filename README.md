# XHS2IG - 小红书 to Instagram 视频处理工具

一个自动化工具，用于从小红书下载视频，进行智能剪辑，输出适合 Instagram/TikTok/YouTube Shorts 的竖版视频。

## 功能特性

- ✅ 小红书视频下载（Playwright）
- ✅ 智能视频剪辑（FFmpeg）
  - Logo 水印叠加
  - BGM 替换
  - 水平镜像翻转
  - 调速
  - 调色（亮度/对比度/饱和度）
  - 9:16 竖屏比例
- ✅ Web 界面操作
- ✅ 批量处理支持

## 技术栈

- **后端**: Python + Flask
- **视频处理**: FFmpeg
- **浏览器自动化**: Playwright
- **前端**: HTML + JavaScript

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/xhs2ig.git
cd xhs2ig

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

## 使用

```bash
# 启动 Web 服务
python app_simple.py

# 访问 http://localhost:5000
```

## 目录结构

```
xhs2ig/
├── app_simple.py          # Flask 主应用
├── core/
│   ├── downloader_pw.py   # 小红书下载器
│   ├── editor_advanced.py # 视频编辑器
│   └── publish_assistant.py # 发布助手
├── templates/
│   └── index.html         # Web 界面
├── assets/
│   ├── logos/             # Logo 文件
│   └── bgm/               # BGM 文件
├── videos/raw/            # 原始视频
├── output/                # 剪辑后视频
└── config/                # 配置文件
```

## 配置

### 视频剪辑默认参数

- 裁剪首尾: 0.5秒
- 播放速度: 1.05x
- Logo 大小: 10%
- 输出比例: 9:16 (1080x1920)

### 自定义配置

编辑 `core/editor_advanced.py` 中的 `PRESETS` 字典。

## 注意事项

1. 小红书链接有时效性，请使用最新分享的链接
2. 视频剪辑需要 FFmpeg 已安装
3. 建议仅用于个人学习和合法用途

## License

MIT
