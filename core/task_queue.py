"""
任务队列管理器 - 支持多用户的任务调度
使用 SQLite 持久化 + 内存队列加速
"""

import sqlite3
import json
import threading
import queue
import sys
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


class TaskType(Enum):
    """任务类型"""
    DOWNLOAD = "download"    # 下载
    EDIT = "edit"            # 剪辑
    PUBLISH = "publish"      # 发布


class Task:
    """任务对象"""
    def __init__(self, task_type: TaskType, user_id: str, params: Dict,
                 task_id: str = None, priority: int = 0):
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self.task_type = task_type
        self.user_id = user_id
        self.params = params
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.finished_at = None
        self.result = None
        self.error = None
        self.progress = 0  # 0-100
        
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "user_id": self.user_id,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "progress": self.progress,
            "result": self.result,
            "error": self.error
        }


class TaskQueue:
    """任务队列管理器 (单例模式)"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
            
        self.db_path = db_path or str(Path(__file__).parent.parent / "data" / "tasks.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 内存队列 (优先级队列)
        self._queue = queue.PriorityQueue()
        
        # 任务字典 (快速查找)
        self._tasks: Dict[str, Task] = {}
        self._tasks_lock = threading.Lock()
        
        # 运行中的任务
        self._running_task: Optional[Task] = None
        self._running_lock = threading.Lock()
        
        # 回调函数
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # 初始化数据库
        self._init_db()
        
        # 启动后台工作线程
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
        # 加载未完成的任务
        self._load_pending_tasks()
        
        self._initialized = True
        print(f"✅ 任务队列初始化完成: {self.db_path}")
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    result TEXT,
                    error TEXT,
                    progress INTEGER DEFAULT 0
                )
            """)
            conn.commit()
    
    def _load_pending_tasks(self):
        """加载未完成的任务到队列"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status IN (?, ?)",
                (TaskStatus.PENDING.value, TaskStatus.RUNNING.value)
            )
            for row in cursor.fetchall():
                task = self._row_to_task(row)
                with self._tasks_lock:
                    self._tasks[task.task_id] = task
                if task.status == TaskStatus.PENDING:
                    self._queue.put((-task.priority, task.created_at.timestamp(), task))
    
    def _row_to_task(self, row) -> Task:
        """数据库行转任务对象"""
        task = Task(
            task_type=TaskType(row[1]),
            user_id=row[2],
            params=json.loads(row[3]),
            task_id=row[0]
        )
        task.status = TaskStatus(row[4])
        task.priority = row[5]
        task.created_at = datetime.fromisoformat(row[6])
        if row[7]:
            task.started_at = datetime.fromisoformat(row[7])
        if row[8]:
            task.finished_at = datetime.fromisoformat(row[8])
        task.result = json.loads(row[9]) if row[9] else None
        task.error = row[10]
        task.progress = row[11] or 0
        return task
    
    def _save_task(self, task: Task):
        """保存任务到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks 
                (task_id, task_type, user_id, params, status, priority, 
                 created_at, started_at, finished_at, result, error, progress)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.task_type.value,
                task.user_id,
                json.dumps(task.params),
                task.status.value,
                task.priority,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.finished_at.isoformat() if task.finished_at else None,
                json.dumps(task.result) if task.result else None,
                task.error,
                task.progress
            ))
            conn.commit()
    
    def submit(self, task_type: TaskType, user_id: str, params: Dict,
               priority: int = 0) -> Task:
        """
        提交任务
        
        Args:
            task_type: 任务类型
            user_id: 用户ID
            params: 任务参数
            priority: 优先级 (越大越优先)
            
        Returns:
            Task 对象
        """
        task = Task(task_type, user_id, params, priority=priority)
        
        with self._tasks_lock:
            self._tasks[task.task_id] = task
        
        # 保存到数据库
        self._save_task(task)
        
        # 加入队列 (使用负数实现高优先级在前)
        self._queue.put((-priority, task.created_at.timestamp(), task))
        
        print(f"📥 任务加入队列 [{task.task_id}] {task_type.value} - {user_id}")
        
        # 触发回调
        self._trigger_callbacks("submit", task)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def get_user_tasks(self, user_id: str, limit: int = 20) -> List[Task]:
        """获取用户的任务列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT * FROM tasks WHERE user_id = ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            )
            return [self._row_to_task(row) for row in cursor.fetchall()]
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        with sqlite3.connect(self.db_path) as conn:
            pending = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?",
                (TaskStatus.PENDING.value,)
            ).fetchone()[0]
            
            running = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?",
                (TaskStatus.RUNNING.value,)
            ).fetchone()[0]
            
            completed = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status IN (?, ?)",
                (TaskStatus.SUCCESS.value, TaskStatus.FAILED.value)
            ).fetchone()[0]
        
        with self._running_lock:
            current_task = self._running_task
        
        return {
            "pending": pending,
            "running": running,
            "completed": completed,
            "current_task": current_task.to_dict() if current_task else None
        }
    
    def cancel_task(self, task_id: str, user_id: str) -> bool:
        """取消任务"""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task or task.user_id != user_id:
                return False
            
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.finished_at = datetime.now()
                self._save_task(task)
                self._trigger_callbacks("cancel", task)
                return True
            
            return False
    
    def update_progress(self, task_id: str, progress: int, message: str = None):
        """更新任务进度"""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = min(100, max(0, progress))
                if message:
                    task.result = {"message": message, **(task.result or {})}
                self._save_task(task)
                self._trigger_callbacks("progress", task)
    
    def on(self, event: str, callback: Callable):
        """注册回调函数"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, task: Task):
        """触发回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(task)
            except Exception as e:
                print(f"回调执行失败: {e}")
    
    def _worker_loop(self):
        """后台工作线程主循环"""
        import subprocess
        import sys
        
        base_dir = Path(__file__).parent.parent
        
        while True:
            try:
                # 获取任务 (阻塞等待)
                _, _, task = self._queue.get()
                
                # 检查是否已取消
                if task.status != TaskStatus.PENDING:
                    continue
                
                # 标记为运行中
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                self._save_task(task)
                
                with self._running_lock:
                    self._running_task = task
                
                self._trigger_callbacks("start", task)
                
                print(f"▶️ 开始执行任务 [{task.task_id}] {task.task_type.value}")
                
                # 执行任务
                try:
                    if task.task_type == TaskType.DOWNLOAD:
                        result = self._execute_download(task, base_dir)
                    elif task.task_type == TaskType.EDIT:
                        result = self._execute_edit(task, base_dir)
                    elif task.task_type == TaskType.PUBLISH:
                        result = self._execute_publish(task, base_dir)
                    else:
                        result = {"success": False, "error": "未知任务类型"}
                    
                    if result.get("success"):
                        task.status = TaskStatus.SUCCESS
                        task.result = result
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = result.get("error", "执行失败")
                    
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    print(f"❌ 任务执行失败 [{task.task_id}]: {e}")
                
                task.finished_at = datetime.now()
                self._save_task(task)
                
                with self._running_lock:
                    self._running_task = None
                
                self._trigger_callbacks("finish", task)
                
                print(f"✅ 任务完成 [{task.task_id}] {task.status.value}")
                
            except Exception as e:
                print(f"工作线程异常: {e}")
    
    def _execute_download(self, task: Task, base_dir: Path) -> Dict:
        """执行下载任务"""
        import asyncio
        sys.path.insert(0, str(base_dir / "core"))
        from downloader_pw import XHSPlaywrightDownloader
        
        url = task.params.get("url")
        user_dir = base_dir / "users" / task.user_id
        raw_dir = user_dir / "videos" / "raw"
        
        async def do_download():
            dl = XHSPlaywrightDownloader(raw_dir=str(raw_dir), headless=True)
            return await dl.download(url)
        
        return asyncio.run(do_download())
    
    def _execute_edit(self, task: Task, base_dir: Path) -> Dict:
        """执行剪辑任务"""
        sys.path.insert(0, str(base_dir / "core"))
        from editor_advanced import AdvancedVideoEditor
        
        note_id = task.params.get("note_id")
        config = task.params.get("config", {})
        
        user_dir = base_dir / "users" / task.user_id
        raw_dir = user_dir / "videos" / "raw"
        output_dir = user_dir / "output"
        
        editor = AdvancedVideoEditor(
            raw_dir=str(raw_dir),
            edited_dir=str(output_dir),
            assets_dir=str(base_dir / "assets"),
            logos_dir=str(base_dir / "assets" / "logos"),
            bgm_dir=str(base_dir / "assets" / "bgm")
        )
        
        video_path = editor.raw_dir / f"{note_id}.mp4"
        
        if not video_path.exists():
            return {"success": False, "error": "原始视频不存在"}
        
        output = editor.edit_video(video_path, config)
        
        if output:
            return {
                "success": True,
                "output_path": str(output),
                "output_name": Path(output).name
            }
        else:
            return {"success": False, "error": "剪辑失败"}
    
    def _execute_publish(self, task: Task, base_dir: Path) -> Dict:
        """执行发布任务"""
        import asyncio
        sys.path.insert(0, str(base_dir / "core"))
        from publisher import PublishManager
        
        video_path = task.params.get("video_path")
        platforms = task.params.get("platforms", [])
        caption = task.params.get("caption", "")
        hashtags = task.params.get("hashtags", [])
        
        async def do_publish():
            manager = PublishManager()
            results = await manager.publish(video_path, platforms, caption, hashtags)
            
            platform_results = []
            for r in results:
                platform_results.append({
                    "platform": r.platform,
                    "success": r.success,
                    "url": r.url,
                    "error": r.error
                })
            
            return {
                "success": any(r.success for r in results),
                "results": platform_results
            }
        
        return asyncio.run(do_publish())


# 全局任务队列实例
task_queue = TaskQueue()
