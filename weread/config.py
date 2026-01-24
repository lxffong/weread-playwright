import os


class Config:
    def __init__(self):
        self.data = self._default_config()
        self._apply_env_overrides()

    def _default_config(self) -> dict:
        return {
            "browser": {"headless": False},
            "cookies_file": "data/cookies.json",
            "reading": {
                "book_ids": [],
                "book_index": None,
                "speed": "medium",
                "page_time_min": 3,
                "page_time_max": 8,
                "turn_time_min": 0.5,
                "turn_time_max": 1.5,
                "duration_minutes": 30,
                "loop_to_first": True,
            },
            "schedule": {"enabled": False, "cron": "0 9 * * *"},
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "from": "",
                    "to": "",
                    "password": "",
                    "security": "auto",  # auto, ssl, tls, none
                },
                "bark": {"enabled": False, "url": ""},
            },
            "stats_file": "data/stats.json",
        }

    def _apply_env_overrides(self):
        env_map = {
            "WEREAD_HEADLESS": ("browser.headless", lambda v: v.lower() == "true"),
            "WEREAD_COOKIES_FILE": ("cookies_file", str),
            "WEREAD_BOOK_IDS": (
                "reading.book_ids",
                lambda v: [u.strip() for u in v.split(",")],
            ),
            "WEREAD_BOOK_INDEX": (
                "reading.book_index",
                lambda v: int(v) if v.isdigit() else None,
            ),
            "WEREAD_SPEED": ("reading.speed", str),
            "WEREAD_DURATION": ("reading.duration_minutes", int),
            "WEREAD_SCHEDULE_ENABLED": (
                "schedule.enabled",
                lambda v: v.lower() == "true",
            ),
            "WEREAD_SCHEDULE_CRON": ("schedule.cron", str),
            "WEREAD_EMAIL_ENABLED": (
                "notifications.email.enabled",
                lambda v: v.lower() == "true",
            ),
            "WEREAD_EMAIL_SMTP": ("notifications.email.smtp_server", str),
            "WEREAD_EMAIL_PORT": ("notifications.email.smtp_port", int),
            "WEREAD_EMAIL_FROM": ("notifications.email.from", str),
            "WEREAD_EMAIL_TO": ("notifications.email.to", str),
            "WEREAD_EMAIL_PASSWORD": ("notifications.email.password", str),
            "WEREAD_EMAIL_SECURITY": ("notifications.email.security", str),
            "WEREAD_BARK_ENABLED": (
                "notifications.bark.enabled",
                lambda v: v.lower() == "true",
            ),
            "WEREAD_BARK_URL": ("notifications.bark.url", str),
        }

        for env_key, (config_key, converter) in env_map.items():
            value = os.getenv(env_key)
            if value is not None:
                keys = config_key.split(".")
                target = self.data
                for k in keys[:-1]:
                    target = target.setdefault(k, {})
                target[keys[-1]] = converter(value)

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
