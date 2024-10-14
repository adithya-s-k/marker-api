from fastapi import UploadFile, File
from celery.result import AsyncResult
from fastapi.responses import JSONResponse
from marker_api.celery_tasks import convert_pdf_to_markdown
import logging
import asyncio

logger = logging.getLogger(__name__)


async def celery_live_root():
    return {"message": "Celery is live. Available API: /convert_pdf, /result"}


async def celery_convert_pdf(pdf_file: UploadFile = File(...)):
    contents = await pdf_file.read()
    task_id = convert_pdf_to_markdown.delay(pdf_file.filename, contents)
    return {"task_id": str(task_id), "status": "Processing"}


async def celery_result(task_id: str):
    task = AsyncResult(task_id)
    if not task.ready():
        return JSONResponse(
            status_code=202, content={"task_id": str(task_id), "status": "Processing"}
        )
    result = task.get()
    return {"task_id": task_id, "status": "Success", "result": result}


async def celery_offline_root():
    return {"message": "Celery is offline. No API is available."}


async def celery_convert_pdf_sync(pdf_file: UploadFile = File(...)):
    contents = await pdf_file.read()
    task = convert_pdf_to_markdown.delay(pdf_file.filename, contents)
    result = task.get(timeout=600)  # 10-minute timeout
    return {"status": "Success", "result": result}


async def celery_convert_pdf_concurrent_await(pdf_file: UploadFile = File(...)):
    contents = await pdf_file.read()

    # Start the Celery task
    task = convert_pdf_to_markdown.delay(pdf_file.filename, contents)

    # Define an asynchronous function to check task status
    async def check_task_status():
        while True:
            if task.ready():
                return task.get()
            await asyncio.sleep(1)  # Wait for 1 second before checking again

    try:
        # Wait for the task to complete with a timeout
        result = await asyncio.wait_for(
            check_task_status(), timeout=600
        )  # 10-minute timeout
        return {"status": "Success", "result": result}
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={"status": "Timeout", "message": "Task processing took too long"},
        )
