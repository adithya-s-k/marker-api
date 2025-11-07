from celery import Task
from marker_api.celery_worker import celery_app
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.logger import configure_logging
import io
import os
import time
import base64
import tempfile
from PIL import Image
import logging
from marker_api.utils import process_image_to_base64
from celery.signals import worker_process_init
from marker_api.routes import process_document_file

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

converter = None

@worker_process_init.connect
def initialize_models(**kwargs):
    global converter
    if not converter:
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
        logger.debug("Marker converter initialized at worker startup")


class DocumentConversionTask(Task):
    _model_dict = None

    @property
    def model_dict(self):
        if self._model_dict is None:
            self._model_dict = create_model_dict()
        return self._model_dict


@celery_app.task(
    ignore_result=False, bind=True, base=DocumentConversionTask, name="convert_document"
)
def convert_pdf_to_markdown(self, filename, file_content, extract_images: bool = True, paginate: bool = True):
    """
    Convert a PDF file to markdown.
    
    Args:
        filename (str): The original filename
        file_content (bytes): The PDF file content
        extract_images (bool): Whether to extract images
        paginate (bool): Whether to split output into pages
    
    Returns:
        dict: Processing results matching PDFConversionResult schema
    """
    return process_document_file(
        file_content, 
        filename=filename, 
        model_dict=self.model_dict, 
        extract_images=extract_images,
        paginate=paginate
    )


@celery_app.task(
    ignore_result=False, bind=True, base=DocumentConversionTask, name="process_batch"
)
def process_batch(self, batch_data):
    """
    Process multiple documents in batch.
    
    Args:
        batch_data (list): List of tuples (filename, content, extract_images, paginate)
    
    Returns:
        list: List of processing results
    """
    results = []
    total_files = len(batch_data)
    
    for i, (filename, content, extract_images, paginate) in enumerate(batch_data, 1):
        try:
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": total_files,
                    "status": f"Processing {filename}"
                }
            )
            
            # Process the document
            result = process_document_file(
                content,
                filename=filename,
                model_dict=self.model_dict,
                extract_images=extract_images,
                paginate=paginate
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            results.append({
                "filename": filename,
                "markdown": "" if not paginate else [],
                "metadata": {
                    "custom_metadata": {"error": str(e)},
                },
                "images": {},
                "status": "error"
            })
    
    return results 