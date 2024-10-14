import argparse
import uvicorn
import logging
from fastapi import FastAPI
from celery.exceptions import TimeoutError
from fastapi.middleware.cors import CORSMiddleware
from marker_api.celery_worker import celery_app
from marker_api.utils import print_markerapi_text_art
from marker.logger import configure_logging
from marker_api.celery_routes import (
    celery_live_root,
    celery_convert_pdf,
    celery_result,
    celery_convert_pdf_concurrent_await,
)


# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

# Global variable to hold model list
app = FastAPI()

logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


def is_celery_alive() -> bool:
    logger.debug("Checking if Celery is alive")
    try:
        result = celery_app.send_task("celery.ping")
        result.get(timeout=3)
        logger.info("Celery is alive")
        return True
    except (TimeoutError, Exception) as e:
        logger.warning(f"Celery is not responding: {str(e)}")
        return False


def setup_routes(app: FastAPI, celery_live: bool):
    logger.info("Setting up routes")
    if celery_live:
        logger.info("Adding Celery routes")
        app.add_api_route(
            "/convert", celery_convert_pdf_concurrent_await, methods=["POST"]
        )

        app.add_api_route("/celery/live", celery_live_root, methods=["GET"])
        app.add_api_route("/celery/convert", celery_convert_pdf, methods=["POST"])
        app.add_api_route("/celery/result/{task_id}", celery_result, methods=["GET"])
        # Add the new real-time endpoint
        logger.info("Adding real-time conversion route")
    else:
        logger.warning("Celery routes not added as Celery is not alive")


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
