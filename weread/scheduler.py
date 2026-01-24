import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class Scheduler:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.scheduler = AsyncIOScheduler()

    def add_job(self, func, cron_expr: str):
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
            self.scheduler.add_job(func, trigger)
            self.logger.info(f"已添加定时任务: {cron_expr}")
        except Exception as e:
            self.logger.error(f"添加定时任务失败: {e}")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("定时任务已启动")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("定时任务已停止")
