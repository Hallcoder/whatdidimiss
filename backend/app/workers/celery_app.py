from celery import Celery

from app.config import settings

celery_app = Celery("whatdidimiss")

celery_app.config_from_object(
    {
        "broker_url": settings.redis_url,
        "result_backend": settings.redis_url.replace("/0", "/1") if "/0" in settings.redis_url else settings.redis_url,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_track_started": True,
        "task_acks_late": True,
        "worker_prefetch_multiplier": 1,
        "task_soft_time_limit": 600,
        "task_time_limit": 900,
        "task_default_retry_delay": 30,
        "task_max_retries": 3,
    }
)

celery_app.autodiscover_tasks(["app.workers"], related_name="video_tasks")
