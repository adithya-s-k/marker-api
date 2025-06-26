import os
from celery import Celery
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv(".env")

# Get Redis host from environment or use default
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_url = f"redis://{redis_host}:6379/0"
logger.info(f"Connecting to Redis at: {redis_url}")

celery_app = Celery(
    "celery_app",
    broker=redis_url,
    backend=redis_url,
    include=["marker_api.celery_tasks"],
)

# Add some debug configuration
celery_app.conf.update(
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

@celery_app.task(name="celery.ping")
def ping():
    logger.info("Ping task received!")
    return "pong"
