import traceback
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class Scheduler:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        # 从配置读取时区，默认 Asia/Shanghai
        tz_str = config.get("scheduler.timezone", "Asia/Shanghai")
        self.timezone = ZoneInfo(tz_str)
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)

    def _log_event(self, event):
        job_id = getattr(event, "job_id", "N/A")
        self.logger.info(f"任务事件: {event.code} - {job_id}")

        # 记录异常信息
        if hasattr(event, "exception") and event.exception:
            self.logger.error(f"任务执行异常: {event.exception}")
            self.logger.error(f"异常详情: {traceback.format_exception(type(event.exception), event.exception, event.exception.__traceback__)}")

    def add_job(
        self, func: Callable, cron_expr: str, args: Optional[tuple] = None
    ) -> Optional[str]:
        """添加定时任务

        Args:
            func: 要执行的函数
            cron_expr: cron 表达式
            args: 函数参数（可选）

        Returns:
            任务 ID，失败时返回 None
        """
        # 参数验证
        if func is None:
            self.logger.error("添加定时任务失败: 函数不能为 None")
            return None

        if not cron_expr or not isinstance(cron_expr, str):
            self.logger.error("添加定时任务失败: cron 表达式无效")
            return None

        try:
            trigger = CronTrigger.from_crontab(cron_expr, timezone=self.timezone)
            job = self.scheduler.add_job(func, trigger, args=args)
            self.logger.info(f"已添加定时任务: {cron_expr}")
            self.logger.info(f"当前时区: {self.timezone}")
            return job.id
        except Exception as e:
            self.logger.error(f"添加定时任务失败: {e}\n{traceback.format_exc()}")
            return None

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            # 只监听任务执行和错误事件，避免日志过于冗长
            self.scheduler.add_listener(
                self._log_event, mask=EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )
            self.scheduler.start()
            self.logger.info("定时任务已启动")
            # 打印所有任务
            jobs = self.scheduler.get_jobs()
            self.logger.info(f"已注册的任务数量: {len(jobs)}")
            for job in jobs:
                next_run = getattr(job, "next_run_time", "N/A")
                self.logger.info(f"  - 任务ID: {job.id}, 下次执行: {next_run}")

    def shutdown(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("定时任务已停止")

    def remove_job(self, job_id: str) -> bool:
        """移除指定任务

        Args:
            job_id: 任务 ID

        Returns:
            成功返回 True，失败返回 False
        """
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"已移除任务: {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"移除任务失败: {e}")
            return False

    def get_jobs(self):
        """获取所有任务列表"""
        return self.scheduler.get_jobs()
