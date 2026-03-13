"""
任务队列管理
"""
import json
from pathlib import Path
from datetime import datetime


class PublishQueue:
    """发布队列管理"""
    
    def __init__(self, queue_file="queue.json"):
        self.queue_file = Path(queue_file)
        self.queue = self._load()
    
    def _load(self):
        """加载队列"""
        if self.queue_file.exists():
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"pending": [], "published": [], "failed": []}
    
    def _save(self):
        """保存队列"""
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(self.queue, f, indent=2, ensure_ascii=False)
    
    def add(self, video_path, url=None, caption="", priority=0):
        """添加任务到队列"""
        task = {
            "id": len(self.queue["pending"]) + len(self.queue["published"]) + len(self.queue["failed"]),
            "video_path": video_path,
            "source_url": url,
            "caption": caption,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        self.queue["pending"].append(task)
        self._save()
        print(f"✅ 已添加到队列: {task['id']}")
        return task
    
    def get_next(self):
        """获取下一个待发布任务"""
        if not self.queue["pending"]:
            return None
        
        # 按优先级排序
        self.queue["pending"].sort(key=lambda x: x.get("priority", 0), reverse=True)
        return self.queue["pending"][0]
    
    def mark_published(self, task_id, media_id=None):
        """标记为已发布"""
        for i, task in enumerate(self.queue["pending"]):
            if task["id"] == task_id:
                task["status"] = "published"
                task["published_at"] = datetime.now().isoformat()
                task["media_id"] = media_id
                self.queue["published"].append(task)
                self.queue["pending"].pop(i)
                self._save()
                return True
        return False
    
    def mark_failed(self, task_id, error=""):
        """标记为失败"""
        for i, task in enumerate(self.queue["pending"]):
            if task["id"] == task_id:
                task["status"] = "failed"
                task["error"] = error
                task["failed_at"] = datetime.now().isoformat()
                self.queue["failed"].append(task)
                self.queue["pending"].pop(i)
                self._save()
                return True
        return False
    
    def stats(self):
        """统计信息"""
        return {
            "pending": len(self.queue["pending"]),
            "published": len(self.queue["published"]),
            "failed": len(self.queue["failed"])
        }


if __name__ == "__main__":
    # 测试
    q = PublishQueue()
    print("Queue stats:", q.stats())
