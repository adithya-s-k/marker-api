import os
import asyncio
import argparse
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import concurrent.futures
from marker.logger import configure_logging  # Import logging configuration
from marker.models import load_all_models  # Import function to load models
from marker_api.routes import (
    process_pdf_file,
)
from marker_api.utils import print_markerapi_text_art
from contextlib import asynccontextmanager
import logging
import gradio as gr
from marker_api.model.schema import (
    BatchConversionResponse,
    ConversionResponse,
    HealthResponse,
    ServerType,
)
from marker_api.demo import demo_ui
from typing import Union

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

# Global variable to hold model list
model_list = None


# Event that runs on startup to load all models
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_list
    logger.debug("--------------------- Loading OCR Model -----------------------")
    print_markerapi_text_art()
    model_list = load_all_models()
    yield


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app = gr.mount_gradio_app(app, demo_ui, path="")


@app.get("/health", response_model=HealthResponse)
def server():
    """
    Root endpoint to check server status.
    """
    return HealthResponse(message="Welcome to Marker-api", type=ServerType.simple)


# Endpoint to convert a single PDF to markdown
@app.post("/convert", response_model=ConversionResponse)
async def convert_pdf_to_markdown(pdf_file: UploadFile, max_pages: Union[int, None] = 10,
                                  start_page: Union[int, None] = 0, langs: Union[str, None] = None,
                                  batch_multiplier: Union[int, None] =  2):
    """
    Endpoint to convert a single PDF to markdown.
    """
    logger.debug(f"Received file: {pdf_file.filename}")
    file = await pdf_file.read()
    response = process_pdf_file(file, pdf_file.filename, model_list,
                                max_pages=max_pages, start_page=start_page,
                                langs=langs, batch_multiplier=batch_multiplier)
    return ConversionResponse(status="Success", result=response)


# Endpoint to convert multiple PDFs to markdown
@app.post("/batch_convert", response_model=BatchConversionResponse)
async def convert_pdfs_to_markdown(pdf_files: List[UploadFile] = File(...)):
    """
    Endpoint to convert multiple PDFs to markdown.
    """
    logger.debug(f"Received {len(pdf_files)} files for batch conversion")

    async def process_files(files):
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            coroutines = [
                loop.run_in_executor(
                    pool, process_pdf_file, await file.read(), file.filename, model_list
                )
                for file in files
            ]
            return await asyncio.gather(*coroutines)

    responses = await process_files(pdf_files)
    return BatchConversionResponse(results=responses)


# Main function to run the server
def main():
    parser = argparse.ArgumentParser(description="Run the marker-api server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=8080, help="Port number")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("server:app", host=args.host, port=args.port)


# Entry point to start the server
if __name__ == "__main__":
    main()
