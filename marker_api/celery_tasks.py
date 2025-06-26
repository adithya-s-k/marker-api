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
    abstract = True
    
    def __init__(self):
        super().__init__()
    
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


def parse_document_and_return_markdown(file_bytes: bytes, filename: str, extract_images: bool = False):
    """
    Function to parse a document (PDF, DOCX, etc.) and extract text and images.
    
    Args:
    file_bytes (bytes): The content of the document file.
    filename (str): Original filename to determine file type
    extract_images (bool): Whether to extract images or not.
    
    Returns:
    tuple: A tuple containing the full text, metadata, and image data.
    """
    try:
        start_time = time.time()
        
        # Create a temporary file with the correct extension
        file_extension = os.path.splitext(filename)[1].lower() if filename else '.pdf'
        
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        
        try:
            # Convert document using the global converter
            rendered = converter(temp_file_path)
            
            # Extract text and metadata from rendered output
            full_text, _, images = text_from_rendered(rendered)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"Document processing completed in {processing_time:.2f} seconds")
            logger.info(f"Extracted text length: {len(full_text)} characters")
            logger.info(f"Images extracted: {len(images) if images else 0}")
            
            # Process images if extraction is enabled
            image_data = {}
            if extract_images and images:
                # Handle different types of images return value
                if isinstance(images, dict):
                    for image_name, image_obj in images.items():
                        try:
                            if isinstance(image_obj, Image.Image):
                                # Handle PIL Image objects
                                image_data[image_name] = process_image_to_base64(image_obj, image_name)
                            else:
                                logger.warning(f"Unexpected image data type for {image_name}: {type(image_obj)}")
                        except Exception as img_error:
                            logger.error(f"Error processing image {image_name}: {str(img_error)}")
                            continue
                else:
                    logger.info(f"Images returned as {type(images)}: {images}")
            
            return full_text, image_data, processing_time
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise


@celery_app.task(
    ignore_result=False, bind=True, base=DocumentConversionTask, name="convert_document"
)
def convert_document_to_markdown(self, filename, file_content, extract_images: bool = True):
    """
    Process a document file (PDF, DOCX, etc.) and return markdown text with metadata.
    
    Args:
        filename (str): The original filename
        file_content (bytes): The document file content
        extract_images (bool): Whether to extract images
    
    Returns:
        dict: Processing results matching PDFConversionResult schema
    """
    try:
        # Determine file type from filename
        file_extension = os.path.splitext(filename)[1].lower() if filename else '.pdf'
        supported_extensions = ['.pdf', '.docx', '.pptx', '.xlsx', '.html', '.epub']
        
        if file_extension not in supported_extensions:
            raise ValueError(f"Unsupported file format: {file_extension}. Supported formats: {supported_extensions}")
        
        logger.info(f"Processing {file_extension} file: {filename}")
        
        full_text, images, processing_time = parse_document_and_return_markdown(
            file_content, filename, extract_images
        )
        
        # Convert metadata to match GeneralMetadata schema
        general_metadata = {
            "custom_metadata": {
                "processing_time": processing_time,
                "file_type": file_extension,
                "text_length": len(full_text),
            },
        }
        
        result = {
            "filename": filename or f"document{file_extension}",
            "markdown": full_text,
            "metadata": general_metadata,
            "images": images if extract_images else {},
            "status": "success"
        }
        
        logger.info(f"Successfully processed {filename}: {len(full_text)} chars, {len(images) if extract_images else 0} images")
        return result
        
    except Exception as e:
        logger.error(f"Error in convert_document_to_markdown: {str(e)}")
        return {
            "filename": filename,
            "markdown": "",
            "metadata": {
                "custom_metadata": {"error": str(e), "file_type": file_extension if filename else ".pdf"},
            },
            "images": {},
            "status": "error"
        }


@celery_app.task(
    ignore_result=False, bind=True, base=DocumentConversionTask, name="process_batch"
)
def process_batch(self, batch_data, extract_images: bool = False):
    """
    Process a batch of documents.
    
    Args:
        batch_data: List of tuples containing (filename, file_content)
        extract_images (bool): Whether to extract images from documents
        
    Returns:
        list: List of processing results for each document
    """
    results = []
    total = len(batch_data)
    
    for i, (filename, file_content) in enumerate(batch_data, start=1):
        try:
            result = convert_document_to_markdown(filename, file_content, extract_images)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            results.append({
                "filename": filename,
                "markdown": "",
                "metadata": {
                    "custom_metadata": {"error": str(e)},
                },
                "images": {},
                "status": "error"
            })

        # Update progress
        self.update_state(state="PROGRESS", meta={"current": i, "total": total})

    return results

# Keep the old function name for backward compatibility
convert_pdf_to_markdown = convert_document_to_markdown 