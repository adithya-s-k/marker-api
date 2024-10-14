import os
from celery import Celery
from dotenv import load_dotenv
import multiprocessing

multiprocessing.set_start_method("spawn")

load_dotenv(".env")

celery_app = Celery(
    "celery_app",
    broker=os.environ.get("REDIS_HOST", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_HOST", "redis://localhost:6379/0"),
    include=["marker_api.celery_tasks"],
)


@celery_app.task(name="celery.ping")
def ping():
    print("Ping task received!")  # or use a logger
    return "pong"
