import os
import time
import base64
from marker.convert import convert_single_pdf
from marker.models import load_all_models
from marker.logger import configure_logging
import logging

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)


# Function to parse PDF and return markdown, metadata, and image data
def parse_pdf_and_return_markdown(pdf_file: bytes, extract_images: bool, model_list):
    """
    Function to parse a PDF and extract text and images.

    Args:
    pdf_file (bytes): The content of the PDF file.
    extract_images (bool): Whether to extract images or not.
    model_list: The model list from load_all_models()

    Returns:
    tuple: A tuple containing the full text, metadata, and image data.
    """
    try:
        start_time = time.time()
        
        # Convert PDF using marker
        full_text, images, out_meta = convert_single_pdf(
            pdf_file, 
            model_list, 
            max_pages=None,
            langs=None,
            batch_multiplier=1,
            start_page=None
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"PDF processing completed in {processing_time:.2f} seconds")
        
        # Process images if extraction is enabled
        image_data = {}
        if extract_images and images:
            for i, image in enumerate(images):
                if image is not None:
                    try:
                        # Check if image is already a PIL Image or needs conversion
                        from PIL import Image as PILImage
                        import io
                        
                        if isinstance(image, str):
                            # If it's a string, it might be a base64 encoded image or file path
                            logger.warning(f"Image {i} is a string: {type(image)}")
                            continue
                        elif hasattr(image, 'save'):
                            # It's a PIL Image object
                            buffer = io.BytesIO()
                            image.save(buffer, format='PNG')
                            img_str = base64.b64encode(buffer.getvalue()).decode()
                            image_data[f"image_{i}"] = img_str
                        else:
                            logger.warning(f"Unknown image type for image {i}: {type(image)}")
                            continue
                    except Exception as img_error:
                        logger.error(f"Error processing image {i}: {str(img_error)}")
                        continue
        
        return full_text, out_meta, image_data, processing_time
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise


def process_pdf_file(pdf_file: bytes, filename: str = None, model_list=None, extract_images: bool = True):
    """
    Process a PDF file and return markdown text with metadata.
    
    Args:
        pdf_file (bytes): The PDF file content
        filename (str): The original filename (optional)
        model_list: Pre-loaded models
        extract_images (bool): Whether to extract images
    
    Returns:
        dict: Processing results matching PDFConversionResult schema
    """
    try:
        full_text, metadata, images, processing_time = parse_pdf_and_return_markdown(
            pdf_file, extract_images, model_list
        )
        
        # Convert metadata to match GeneralMetadata schema
        general_metadata = {
            "languages": metadata.get("languages", None),
            "toc": metadata.get("toc", None), 
            "pages": metadata.get("pages", None),
            "custom_metadata": {
                "processing_time": processing_time,
                **metadata
            }
        }
        
        return {
            "filename": filename or "document.pdf",
            "markdown": full_text,
            "metadata": general_metadata,
            "images": images,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error in process_pdf_file: {str(e)}")
        return {
            "filename": filename or "document.pdf",
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
