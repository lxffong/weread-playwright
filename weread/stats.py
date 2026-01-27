import json
from pathlib import Path
from datetime import datetime
from typing import Dict

class Stats:
    def __init__(self, stats_file: str):
        self.stats_file = Path(stats_file)
        self.data = self._load_stats()

    def _load_stats(self) -> Dict:
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'total_sessions': 0, 'total_minutes': 0, 'sessions': []}

    def save(self):
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_session(self, book_name: str, minutes: int):
        self.data['total_sessions'] += 1
        self.data['total_minutes'] += minutes
        self.data['sessions'].append({
            'date': datetime.now().isoformat(),
            'book': book_name,
            'minutes': minutes
        })
        self.save()

    def get_summary(self) -> str:
        return f"总会话: {self.data['total_sessions']}, 总时长: {self.data['total_minutes']}分钟"
