import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class TodoDatabase:
    """Простая база данных для хранения задач"""
    
    def __init__(self, filename: str = "todos.json"):
        self.filename = filename
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Загружает данные из файла"""
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_data(self):
        """Сохраняет данные в файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_todo(self, user_id: int, task: str, timezone: str, 
                 reminder_time: str) -> bool:
        """Добавляет новую задачу"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {"todos": [], "timezone": timezone}
        
        # Проверяем валидность времени
        try:
            datetime.strptime(reminder_time, "%H:%M")
        except ValueError:
            return False
        
        self.data[user_id_str]["timezone"] = timezone
        self.data[user_id_str]["todos"].append({
            "id": len(self.data[user_id_str]["todos"]),
            "task": task,
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "reminder_time": reminder_time
        })
        self._save_data()
        return True
    
    def get_pending_todos(self, user_id: int) -> List[Dict]:
        """Получает незавершённые задачи"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            return []
        return [t for t in self.data[user_id_str]["todos"] if not t["completed"]]
    
    def get_completed_todos(self, user_id: int) -> List[Dict]:
        """Получает завершённые задачи"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            return []
        return [t for t in self.data[user_id_str]["todos"] if t["completed"]]
    
    def complete_todo(self, user_id: int, todo_id: int) -> bool:
        """Отмечает задачу как завершённую"""
        user_id_str = str(user_id)
        if user_id_str in self.data:
            for todo in self.data[user_id_str]["todos"]:
                if todo["id"] == todo_id:
                    todo["completed"] = True
                    self._save_data()
                    return True
        return False
    
    def delete_todo(self, user_id: int, todo_id: int) -> bool:
        """Удаляет задачу"""
        user_id_str = str(user_id)
        if user_id_str in self.data:
            self.data[user_id_str]["todos"] = [
                t for t in self.data[user_id_str]["todos"] if t["id"] != todo_id
            ]
            self._save_data()
            return True
        return False
    
    def get_user_timezone(self, user_id: int) -> str:
        """Получает часовой пояс пользователя"""
        user_id_str = str(user_id)
        if user_id_str in self.data:
            return self.data[user_id_str].get("timezone", "UTC")
        return "UTC"
    
    def add_simple_todo(self, user_id: int, task: str) -> bool:
        """Добавляет простой todo без напоминания"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {"todos": [], "timezone": "UTC", "simple_todos": []}
        
        if "simple_todos" not in self.data[user_id_str]:
            self.data[user_id_str]["simple_todos"] = []
        
        self.data[user_id_str]["simple_todos"].append({
            "id": len(self.data[user_id_str]["simple_todos"]),
            "task": task,
            "completed": False,
            "created_at": datetime.now().isoformat()
        })
        self._save_data()
        return True
    
    def get_simple_todos(self, user_id: int) -> list:
        """Получает все простые todos"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            return []
        return self.data[user_id_str].get("simple_todos", [])
    
    def complete_simple_todo(self, user_id: int, todo_id: int) -> bool:
        """Отмечает простой todo как завершённый"""
        user_id_str = str(user_id)
        if user_id_str in self.data and "simple_todos" in self.data[user_id_str]:
            for todo in self.data[user_id_str]["simple_todos"]:
                if todo["id"] == todo_id:
                    todo["completed"] = True
                    self._save_data()
                    return True
        return False
    
    def delete_simple_todo(self, user_id: int, todo_id: int) -> bool:
        """Удаляет простой todo"""
        user_id_str = str(user_id)
        if user_id_str in self.data and "simple_todos" in self.data[user_id_str]:
            self.data[user_id_str]["simple_todos"] = [
                t for t in self.data[user_id_str]["simple_todos"] if t["id"] != todo_id
            ]
            self._save_data()
            return True
        return False
    
    def add_everyday_reminder(self, user_id: int, task: str, timezone: str, 
                             reminder_time: str) -> bool:
        """Добавляет ежедневное напоминание"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {
                "todos": [], 
                "timezone": timezone,
                "simple_todos": [],
                "everyday_reminders": []
            }
        
        if "everyday_reminders" not in self.data[user_id_str]:
            self.data[user_id_str]["everyday_reminders"] = []
        
        # Проверяем валидность времени
        try:
            datetime.strptime(reminder_time, "%H:%M")
        except ValueError:
            return False
        
        self.data[user_id_str]["timezone"] = timezone
        self.data[user_id_str]["everyday_reminders"].append({
            "id": len(self.data[user_id_str]["everyday_reminders"]),
            "task": task,
            "timezone": timezone,
            "reminder_time": reminder_time,
            "created_at": datetime.now().isoformat(),
            "active": True
        })
        self._save_data()
        return True
    
    def get_everyday_reminders(self, user_id: int) -> List[Dict]:
        """Получает все ежедневные напоминания"""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            return []
        return self.data[user_id_str].get("everyday_reminders", [])
    
    def delete_everyday_reminder(self, user_id: int, reminder_id: int) -> bool:
        """Удаляет ежедневное напоминание"""
        user_id_str = str(user_id)
        if user_id_str in self.data and "everyday_reminders" in self.data[user_id_str]:
            self.data[user_id_str]["everyday_reminders"] = [
                r for r in self.data[user_id_str]["everyday_reminders"] if r["id"] != reminder_id
            ]
            self._save_data()
            return True
        return False
    
    def toggle_everyday_reminder(self, user_id: int, reminder_id: int) -> bool:
        """Включает/выключает ежедневное напоминание"""
        user_id_str = str(user_id)
        if user_id_str in self.data and "everyday_reminders" in self.data[user_id_str]:
            for reminder in self.data[user_id_str]["everyday_reminders"]:
                if reminder["id"] == reminder_id:
                    reminder["active"] = not reminder["active"]
                    self._save_data()
                    return True
        return False
