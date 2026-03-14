#!/usr/bin/env python3
"""
剪辑工作进程 - 支持单用户和多用户模式
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "core")
from editor_advanced import AdvancedVideoEditor

def main():
    base_dir = Path(__file__).parent
    
    # 获取用户ID（单用户模式不传user_id）
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if user_id:
        # 多用户模式
        user_dir = base_dir / "users" / user_id
        raw_dir = user_dir / "videos" / "raw"
        output_dir = user_dir / "output"
        config_file = user_dir / ".temp_config.json"
        result_file = user_dir / ".temp_edit_result.json"
    else:
        # 单用户模式（兼容旧版本）
        raw_dir = base_dir / "videos" / "raw"
        output_dir = base_dir / "output"
        config_file = base_dir / ".temp_config.json"
        result_file = base_dir / ".temp_edit_result.json"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取配置
    if not config_file.exists():
        result = {"success": False, "error": "未找到配置"}
        result_file.write_text(json.dumps(result))
        return
    
    data = json.loads(config_file.read_text(encoding='utf-8'))
    note_id = data["note_id"]
    config = data.get("config", {})
    
    # 剪辑
    editor = AdvancedVideoEditor(
        raw_dir=str(raw_dir),
        edited_dir=str(output_dir),
        assets_dir=str(base_dir / "assets"),
        logos_dir=str(base_dir / "assets" / "logos"),
        bgm_dir=str(base_dir / "assets" / "bgm")
    )
    video_path = editor.raw_dir / f"{note_id}.mp4"
    
    if not video_path.exists():
        result = {"success": False, "error": "原始视频不存在"}
    else:
        try:
            output = editor.edit_video(video_path, config)
            if output:
                result = {
                    "success": True,
                    "output_path": str(output),
                    "output_name": Path(output).name
                }
            else:
                result = {"success": False, "error": "剪辑失败"}
        except Exception as e:
            result = {"success": False, "error": str(e)}
    
    # 保存结果
    result_file.write_text(
        json.dumps(result, ensure_ascii=False),
        encoding='utf-8'
    )

if __name__ == "__main__":
    main()
