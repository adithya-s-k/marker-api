import argparse
import uvicorn
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from celery.exceptions import TimeoutError
from fastapi.middleware.cors import CORSMiddleware
from marker_api.celery_worker import celery_app
from marker_api.utils import print_markerapi_text_art
from marker.logger import configure_logging
from marker_api.celery_routes import (
    celery_convert_pdf,
    celery_result,
    celery_convert_pdf_concurrent_await,
    celery_batch_convert,
    celery_batch_result,
)
# import gradio as gr
# from marker_api.demo import demo_ui
from marker_api.model.schema import (
    BatchConversionResponse,
    BatchResultResponse,
    CeleryResultResponse,
    CeleryTaskResponse,
    ConversionResponse,
    HealthResponse,
    ServerType,
    PDFConversionResult,
)
from typing import List
import os

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

# Global variable to hold model list
app = FastAPI(
    title="Marker API Distributed Server",
    description="Distributed API for converting documents (PDF, DOCX, PPTX, XLSX, HTML, EPUB) to Markdown using marker",
    version="1.7.5"
)

logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health", response_model=HealthResponse)
def server():
    """
    Root endpoint to check server status.

    Returns:
    HealthResponse: A welcome message, server type, and number of workers (if distributed).
    """
    worker_count = len(celery_app.control.inspect().stats() or {})
    server_type = ServerType.distributed if worker_count > 0 else ServerType.simple
    return HealthResponse(
        message="Welcome to Marker-api",
        type=server_type,
        workers=worker_count if server_type == ServerType.distributed else None,
        supported_formats=["PDF", "DOCX", "PPTX", "XLSX", "HTML", "EPUB"]
    )


def is_celery_alive() -> bool:
    logger.debug("Checking if Celery is alive")
    max_retries = 3
    timeout = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            result = celery_app.send_task("celery.ping")
            result.get(timeout=timeout)
            logger.info("Celery is alive")
            return True
        except (TimeoutError, Exception) as e:
            logger.warning(f"Celery connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2)  # Wait 2 seconds before retrying
    
    logger.error("All Celery connection attempts failed")
    return False


def validate_file(file: UploadFile) -> str:
    """Validate uploaded file and return file extension"""
    # Check file size (limit to 50MB)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    
    # Check file type
    allowed_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.html', '.epub'}
    file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ''
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file_extension}. Supported types: {', '.join(allowed_extensions)}"
        )
    
    return file_extension


def setup_routes(app: FastAPI, celery_live: bool):
    logger.info("Setting up routes")
    if celery_live:
        logger.info("Adding Celery routes")

        @app.post("/convert", response_model=ConversionResponse)
        async def convert_document(
            file: UploadFile = File(...),
            extract_images: bool = Form(True)
        ):
            """Convert a document (PDF, DOCX, PPTX, XLSX, HTML, EPUB) to markdown"""
            validate_file(file)
            return await celery_convert_pdf_concurrent_await(file, extract_images)

        @app.post("/celery/convert", response_model=CeleryTaskResponse)
        async def celery_convert_document(
            file: UploadFile = File(...),
            extract_images: bool = Form(True)
        ):
            """Submit a document conversion task to Celery queue"""
            validate_file(file)
            return await celery_convert_pdf(file, extract_images)

        @app.get("/celery/result/{task_id}", response_model=CeleryResultResponse)
        async def get_celery_result(task_id: str):
            return await celery_result(task_id)

        @app.post("/batch_convert", response_model=BatchConversionResponse)
        async def batch_convert(
            files: List[UploadFile] = File(...),
            extract_images: bool = Form(True)
        ):
            """Convert multiple documents to markdown"""
            for file in files:
                validate_file(file)
            return await celery_batch_convert(files, extract_images)

        @app.get("/batch_convert/result/{task_id}", response_model=BatchResultResponse)
        async def get_batch_result(task_id: str):
            return await celery_batch_result(task_id)

        logger.info("Adding real-time conversion route")
    else:
        logger.warning("Celery routes not added as Celery is not alive")
    # app = gr.mount_gradio_app(app, demo_ui, path="")


def parse_args():
    logger.debug("Parsing command line arguments")
    parser = argparse.ArgumentParser(description="Run FastAPI with Uvicorn.")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the FastAPI app"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to run the FastAPI app"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_markerapi_text_art()
    logger.info(f"Starting FastAPI app on {args.host}:{args.port}")
    celery_alive = is_celery_alive()
    setup_routes(app, celery_alive)
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    except Exception as e:
        logger.critical(f"Failed to start the application: {str(e)}")
        raise
