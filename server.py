import os
import asyncio
import argparse
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import concurrent.futures
from marker.logger import configure_logging  # Import logging configuration
from marker.models import create_model_dict  # Import function to create model dict
from marker_api.routes import (
    process_document_file,  # Updated to handle all document types
)
from marker_api.utils import print_markerapi_text_art
from contextlib import asynccontextmanager
import logging
# import gradio as gr
from marker_api.model.schema import (
    BatchConversionResponse,
    ConversionResponse,
    HealthResponse,
    ServerType,
    PDFConversionResult,
)
# from marker_api.demo import demo_ui

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

# Global variable to hold model dict
model_dict = None


# Event that runs on startup to load all models
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_dict
    logger.debug("--------------------- Loading OCR Model -----------------------")
    print_markerapi_text_art()
    model_dict = create_model_dict()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Marker API",
    description="Convert PDF to Markdown with marker-pdf",
    version="1.7.5",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# app = gr.mount_gradio_app(app, demo_ui, path="")


@app.get("/health")
async def health_check():
    return {"message": "Marker API is running", "status": "ok", "version": "1.7.5"}

@app.get("/")
async def root():
    return {"message": "Welcome to Marker-api", "version": "1.7.5"}


# Endpoint to convert a single document to markdown
@app.post("/convert", response_model=PDFConversionResult)
async def convert_document_to_markdown(
    file: UploadFile = File(...),
    extract_images: bool = Form(True)
):
    """
    Endpoint to convert a document (PDF, DOCX, PPTX, XLSX, HTML, EPUB) to markdown.
    """
    global model_dict
    
    if model_dict is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    
    logger.debug(f"Received file: {file.filename}")
    
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
    
    try:
        file_content = await file.read()
        response = process_document_file(
            file_content, 
            filename=file.filename, 
            model_dict=model_dict, 
            extract_images=extract_images
        )
        return PDFConversionResult(**response)
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


# Endpoint to convert multiple documents to markdown
@app.post("/batch_convert", response_model=BatchConversionResponse)
async def convert_documents_to_markdown(
    files: List[UploadFile] = File(...),
    extract_images: bool = Form(True)
):
    """
    Endpoint to convert multiple documents to markdown.
    """
    global model_dict
    
    if model_dict is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    
    logger.debug(f"Received {len(files)} files for batch conversion")

    async def process_files(file_list):
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            coroutines = [
                loop.run_in_executor(
                    pool, 
                    process_document_file, 
                    await file.read(), 
                    file.filename, 
                    model_dict, 
                    extract_images
                )
                for file in file_list
            ]
            return await asyncio.gather(*coroutines)

    responses = await process_files(files)
    return BatchConversionResponse(results=responses)


@app.post("/extract_structured")
async def extract_structured_data(
    file: UploadFile = File(...),
    schema: str = Form(None)
):
    """
    Extract structured data from documents using Pydantic schemas (v1.7.5 feature)
    """
    try:
        # For now, return a placeholder response indicating the feature is available
        # In a full implementation, this would use marker-pdf 1.7.5's structured extraction
        return {
            "message": "Structured extraction endpoint available in v1.7.5",
            "filename": file.filename,
            "feature": "structured_extraction",
            "status": "placeholder_implementation",
            "note": "This would extract structured data using Pydantic schemas in the full implementation"
        }
    except Exception as e:
        logger.error(f"Structured extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Structured extraction failed: {str(e)}")


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
