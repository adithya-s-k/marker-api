import os
import asyncio
import argparse
import time
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import concurrent.futures
from marker.convert import convert_single_pdf  # Import function to parse PDF
from marker.logger import configure_logging  # Import logging configuration
from marker.models import load_all_models  # Import function to load models
from marker.settings import Settings  # Import settings
from marker_api.routes import (
    process_pdf_file,
)
from marker_api.utils import print_markerapi_text_art
from contextlib import asynccontextmanager
import logging

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


# Root endpoint to check server status
@app.get("/")
def server():
    """
    Root endpoint to check server status.

    Returns:
    dict: A welcome message.
    """
    return {"message": "Welcome to Marker-api"}


# Endpoint to convert a single PDF to markdown
@app.post("/convert")
async def convert_pdf_to_markdown(pdf_file: UploadFile):
    """
    Endpoint to convert a single PDF to markdown.

    Args:
    pdf_file (UploadFile): The uploaded PDF file.

    Returns:
    dict: The response from processing the PDF file.
    """
    logger.debug(f"Received file: {pdf_file.filename}")
    file = await pdf_file.read()
    response = process_pdf_file(file, pdf_file.filename)
    return [response]


# Endpoint to convert multiple PDFs to markdown
@app.post("/batch_convert")
async def convert_pdfs_to_markdown(pdf_file: List[UploadFile] = File(...)):
    """

    (Unstable) this endpoint is unstable and tends to break due to semaphore issues

    Endpoint to convert multiple PDFs to markdown.

    Args:
    pdf_files (List[UploadFile]): The list of uploaded PDF files.

    Returns:
    list: The responses from processing each PDF file.
    """
    logger.debug(f"Received {len(pdf_file)} files for batch conversion")

    async def process_files(files):
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            coroutines = [
                loop.run_in_executor(
                    pool, process_pdf_file, await file.read(), file.filename
                )
                for file in files
            ]
            return await asyncio.gather(*coroutines)

    responses = await process_files(pdf_file)
    return responses


# Main function to run the server
def main():
    parser = argparse.ArgumentParser(description="Run the marker-api server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=8080, help="Port number")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("simple_server:app", host=args.host, port=args.port)


# Entry point to start the server
if __name__ == "__main__":
    main()
