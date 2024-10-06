import os
import asyncio
import argparse
import time
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import concurrent.futures
from marker.parse import parse_single_pdf  # Import function to parse PDF
from marker.logger import configure_logging  # Import logging configuration
from marker.models import load_all_models  # Import function to load models
from marker.settings import Settings  # Import settings
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



# Function to parse PDF and return markdown, metadata, and image data
def parse_pdf_and_return_markdown(pdf_file: bytes, extract_images: bool):
    """
    Function to parse a PDF and extract text and images.

    Args:
    pdf_file (bytes): The content of the PDF file.
    extract_images (bool): Whether to extract images or not.

    Returns:
    tuple: A tuple containing the full text, metadata, and image data (if extracted).
    """
    logger.debug("Parsing PDF file")
    full_text, images, out_meta = parse_single_pdf(pdf_file, model_list)
    logger.debug(f"Images extracted: {list(images.keys())}")
    image_data = {}
    if extract_images:
        for i, (filename, image) in enumerate(images.items()):
            logger.debug(f"Processing image {filename}")
            
            # Save image as PNG
            image.save(filename, "PNG")

            # Read the saved image file as bytes
            with open(filename, "rb") as f:
                image_bytes = f.read()

            # Convert image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_data[f'{filename}'] = image_base64

            # Remove the temporary image file
            os.remove(filename)

    return full_text, out_meta, image_data

# Function to process a single PDF file
def process_pdf_file(file_content: bytes, filename: str):
    """
    Function to process a single PDF file.

    Args:
    file_content (bytes): The content of the PDF file.
    filename (str): The name of the PDF file.

    Returns:
    dict: A dictionary containing the filename, markdown text, metadata, image data, status, and processing time.
    """
    entry_time = time.time()
    logger.info(f"Entry time for {filename}: {entry_time}")
    markdown_text, metadata, image_data = parse_pdf_and_return_markdown(file_content, extract_images=True)
    completion_time = time.time()
    logger.info(f"Model processes complete time for {filename}: {completion_time}")
    time_difference = completion_time - entry_time
    return {
        "filename": filename,
        "markdown": markdown_text,
        "metadata": metadata,
        "images": image_data,
        "status": "ok",
        "time": time_difference
    }


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
    Endpoint to convert multiple PDFs to markdown.

    Args:
    pdf_files (List[UploadFile]): The list of uploaded PDF files.

    Returns:
    list: The responses from processing each PDF file.
    """
    logger.debug(f"Received {len(pdf_file)} files for batch conversion")
    async def process_files(files):
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            coroutines = [
                loop.run_in_executor(pool, process_pdf_file, await file.read(), file.filename)
                for file in files
            ]
            return await asyncio.gather(*coroutines)

    responses = await process_files(pdf_file)
    return responses

# Main function to run the server
def main():
    parser = argparse.ArgumentParser(description="Run the marker-api server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()
    
    import uvicorn
    uvicorn.run("server:app", host=args.host, port=args.port)

# Entry point to start the server
if __name__ == "__main__":
    main()
