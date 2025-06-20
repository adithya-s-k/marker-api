import os
import time
import base64
import tempfile
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.logger import configure_logging
import logging

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)


def parse_document_and_return_markdown(file_bytes: bytes, filename: str, extract_images: bool, model_dict):
    """
    Function to parse a document (PDF, DOCX, etc.) and extract text and images.

    Args:
    file_bytes (bytes): The content of the document file.
    filename (str): Original filename to determine file type
    extract_images (bool): Whether to extract images or not.
    model_dict: The model dictionary from create_model_dict()

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
            # Create converter with model dictionary - PdfConverter handles all formats in 1.6.2
            converter = PdfConverter(
                artifact_dict=model_dict,
            )
            
            # Convert document using the new API - pass the file path directly
            rendered = converter(temp_file_path)
            
            # Extract text and metadata from rendered output
            full_text, images, out_meta = text_from_rendered(rendered)
            
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
                    for image_name, image_data_bytes in images.items():
                        try:
                            if isinstance(image_data_bytes, bytes):
                                img_str = base64.b64encode(image_data_bytes).decode()
                                image_data[image_name] = img_str
                            else:
                                logger.warning(f"Unexpected image data type for {image_name}: {type(image_data_bytes)}")
                        except Exception as img_error:
                            logger.error(f"Error processing image {image_name}: {str(img_error)}")
                            continue
                else:
                    logger.info(f"Images returned as {type(images)}: {images}")
            
            return full_text, out_meta, image_data, processing_time
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise


def process_document_file(file_bytes: bytes, filename: str = None, model_dict=None, extract_images: bool = True):
    """
    Process a document file (PDF, DOCX, etc.) and return markdown text with metadata.
    
    Args:
        file_bytes (bytes): The document file content
        filename (str): The original filename (optional)
        model_dict: Pre-loaded model dictionary
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
        
        full_text, metadata, images, processing_time = parse_document_and_return_markdown(
            file_bytes, filename, extract_images, model_dict
        )
        
        # Convert metadata to match GeneralMetadata schema
        general_metadata = {
            "languages": metadata.get("languages", None),
            "toc": metadata.get("toc", None), 
            "pages": metadata.get("pages", None),
            "custom_metadata": {
                "processing_time": processing_time,
                "file_type": file_extension,
                "text_length": len(full_text),
                "images_count": len(images),
                **metadata
            }
        }
        
        result = {
            "filename": filename or f"document{file_extension}",
            "markdown": full_text,
            "metadata": general_metadata,
            "images": images,
            "status": "success"
        }
        
        logger.info(f"Successfully processed {filename}: {len(full_text)} chars, {len(images)} images")
        return result
        
    except Exception as e:
        logger.error(f"Error in process_document_file: {str(e)}")
        return {
            "filename": filename or "document.pdf",
            "markdown": "",
            "metadata": {
                "languages": None,
                "toc": None,
                "pages": None,
                "custom_metadata": {"error": str(e), "file_type": file_extension if filename else ".pdf"}
            },
            "images": {},
            "status": "error"
        }


# Keep the old function for backward compatibility
def process_pdf_file(pdf_file: bytes, filename: str = None, model_dict=None, extract_images: bool = True):
    """
    Process a PDF file and return markdown text with metadata.
    Wrapper around process_document_file for backward compatibility.
    """
    return process_document_file(pdf_file, filename, model_dict, extract_images)
