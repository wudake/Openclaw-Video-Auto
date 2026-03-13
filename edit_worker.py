#!/usr/bin/env python3
"""
剪辑工作进程 - 独立脚本
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "core")
from editor_advanced import AdvancedVideoEditor

def main():
    base_dir = Path(__file__).parent
    
    # 读取配置
    config_file = base_dir / ".temp_config.json"
    if not config_file.exists():
        result = {"success": False, "error": "未找到配置"}
        (base_dir / ".temp_edit_result.json").write_text(json.dumps(result))
        return
    
    data = json.loads(config_file.read_text(encoding='utf-8'))
    note_id = data["note_id"]
    config = data["config"]
    
    # 剪辑
    editor = AdvancedVideoEditor()
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
    (base_dir / ".temp_edit_result.json").write_text(
        json.dumps(result, ensure_ascii=False),
        encoding='utf-8'
    )

if __name__ == "__main__":
    main()
