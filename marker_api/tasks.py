import os
from celery import Celery
from marker.models import create_model_dict
from marker_api.routes import process_document_file
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Redis URL from environment variable
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
celery_app = Celery(
    "marker_api",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Global variable to hold model dictionary
model_dict = None

def load_models():
    """Load marker models once per worker"""
    global model_dict
    if model_dict is None:
        logger.info("Loading marker models...")
        model_dict = create_model_dict()
        logger.info("Models loaded successfully!")
    return model_dict

@celery_app.task(bind=True)
def process_document_task(self, file_content: bytes, filename: str):
    """
    Celery task to process a document (PDF, DOCX, etc.) and convert it to markdown.
    
    Args:
        file_content (bytes): The document file content
        filename (str): The original filename
    
    Returns:
        dict: Processing results
    """
    try:
        # Update task state to PROGRESS
        self.update_state(
            state="PROGRESS",
            meta={"status": "Loading models and processing document..."}
        )
        
        # Load models if not already loaded
        models = load_models()
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": f"Converting {filename}..."}
        )
        
        # Process the document
        result = process_document_file(
            file_content, 
            filename=filename,
            model_dict=models,
            extract_images=True
        )
        
        logger.info(f"Successfully processed document: {filename}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document {filename}: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "filename": filename}
        )
        raise

@celery_app.task(bind=True)
def process_batch_documents_task(self, files_data: list):
    """
    Celery task to process multiple documents in batch.
    
    Args:
        files_data (list): List of dictionaries with 'content' and 'filename' keys
    
    Returns:
        list: List of processing results
    """
    try:
        # Update task state to PROGRESS
        self.update_state(
            state="PROGRESS",
            meta={"status": "Loading models..."}
        )
        
        # Load models if not already loaded
        models = load_models()
        
        results = []
        total_files = len(files_data)
        
        for i, file_data in enumerate(files_data):
            try:
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "status": f"Processing file {i+1}/{total_files}: {file_data['filename']}",
                        "current": i+1,
                        "total": total_files
                    }
                )
                
                # Process the document
                result = process_document_file(
                    file_data['content'],
                    filename=file_data['filename'],
                    model_dict=models,
                    extract_images=True
                )
                
                results.append(result)
                logger.info(f"Successfully processed document {i+1}/{total_files}: {file_data['filename']}")
                
            except Exception as e:
                logger.error(f"Error processing document {file_data['filename']}: {str(e)}")
                error_result = {
                    "filename": file_data['filename'],
                    "markdown": "",
                    "metadata": {
                        "languages": None,
                        "toc": None,
                        "pages": None,
                        "custom_metadata": {"error": str(e)}
                    },
                    "images": {},
                    "status": "error"
                }
                results.append(error_result)
        
        logger.info(f"Batch processing completed. Processed {len(results)} files.")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise 