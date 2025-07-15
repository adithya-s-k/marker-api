import os
import time
import base64
import tempfile
import io
import subprocess
from PIL import Image
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.logger import configure_logging
import logging
from marker_api.utils import process_image_to_base64
from marker.config.parser import ConfigParser

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = ['.pdf', '.docx'] # , '.pptx', '.xlsx', '.html', '.epub']

def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> None:
    """
    Convert DOCX to PDF using LibreOffice.
    
    Args:
        docx_path (str): Path to input DOCX file
        pdf_path (str): Path where to save the PDF file
    """
    try:
        # Convert to absolute paths
        docx_path = os.path.abspath(docx_path)
        pdf_path = os.path.abspath(pdf_path)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Use LibreOffice to convert DOCX to PDF
        # --headless: run without UI
        # --convert-to pdf: convert to PDF format
        # --outdir: specify output directory
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',  # Use the Writer PDF export filter
            '--outdir', os.path.dirname(pdf_path),
            docx_path
        ]
        
        logger.info(f"Converting DOCX to PDF: {docx_path} -> {pdf_path}")
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"LibreOffice conversion failed: {process.stderr}")
            
        # LibreOffice creates the PDF with the same name as input but .pdf extension
        # Move it to the desired location if different
        generated_pdf = os.path.join(
            os.path.dirname(pdf_path),
            os.path.splitext(os.path.basename(docx_path))[0] + '.pdf'
        )
        if generated_pdf != pdf_path and os.path.exists(generated_pdf):
            os.rename(generated_pdf, pdf_path)
            
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to convert DOCX to PDF: {str(e)}")
    except Exception as e:
        raise Exception(f"Error during DOCX to PDF conversion: {str(e)}")

def parse_document_and_return_markdown(file_bytes: bytes, filename: str, extract_images: bool, model_dict, paginate: bool = True):
    """
    Function to parse a document (PDF, DOCX, etc.) and extract text and images.

    Args:
    file_bytes (bytes): The content of the document file.
    filename (str): Original filename to determine file type
    extract_images (bool): Whether to extract images or not.
    model_dict: The model dictionary from create_model_dict()
    paginate (bool): Whether to paginate the output based on original document pages.

    Returns:
    tuple: A tuple containing the full text, metadata, image data, and converted PDF content.
    """
    try:
        start_time = time.time()
        
        # Create a temporary file with the correct extension
        file_extension = os.path.splitext(filename)[1].lower() if filename else '.pdf'
        
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        
        original_temp_path = temp_file_path  # Keep track of original file
        try:
            # If the file is a DOCX, convert it to PDF first
            if file_extension == '.docx':
                pdf_temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                pdf_temp_path = pdf_temp_file.name
                pdf_temp_file.close()
                
                try:
                    convert_docx_to_pdf(temp_file_path, pdf_temp_path)
                    temp_file_path = pdf_temp_path  # Use the converted PDF
                except Exception as e:
                    raise Exception(f"Failed to convert DOCX to PDF: {str(e)}")
            
            # Create converter with model dictionary and pagination config
            config = {
                "paginate_output": paginate,  # Add page breaks
                # "format_lines": True,     # Better formatting
                # "force_ocr": False,       # Don't force OCR for DOCX
                # "strip_existing_ocr": False,  # Keep existing text
                # "disable_image_extraction": True,  # Keep images   
            }
            config_parser = ConfigParser(config)
            # Initialize the converter with config
            converter = PdfConverter(
                artifact_dict=model_dict,
                config=config_parser.generate_config_dict()
            )
            
            # Convert document using the new API - pass the file path directly
            rendered = converter(temp_file_path)
            
            # Extract text and metadata from rendered output
            full_text, _, images = text_from_rendered(rendered)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"Document processing completed in {processing_time:.2f} seconds")
            if isinstance(full_text, list):
                logger.info(f"Extracted {len(full_text)} pages")
                logger.info(f"Total text length: {sum(len(page) for page in full_text)} characters")
            else:
                logger.info(f"Extracted text length: {len(full_text)} characters")
            logger.info(f"Images extracted: {len(images) if images else 0}")
            
            # Process images if extraction is enabled
            image_data = {}
            if extract_images and images:
                for idx, img in enumerate(images):
                    image_data[f"image_{idx}"] = process_image_to_base64(img)
            
            # Get the converted PDF content
            converted_pdf_content = None
            if hasattr(rendered, 'pdf_bytes') and rendered.pdf_bytes:
                converted_pdf_content = base64.b64encode(rendered.pdf_bytes).decode('utf-8')
            elif os.path.exists(temp_file_path):
                # If pdf_bytes not available, read from the temporary file
                with open(temp_file_path, 'rb') as f:
                    converted_pdf_content = base64.b64encode(f.read()).decode('utf-8')
            
            return full_text, image_data, processing_time, converted_pdf_content
            
        finally:
            # Clean up the temporary files
            for path in [original_temp_path, temp_file_path]:
                try:
                    if path and os.path.exists(path):
                        os.unlink(path)
                except OSError:
                    pass  # File already deleted or doesn't exist
                
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise


def process_document_file(file_bytes: bytes, filename: str = None, model_dict=None, extract_images: bool = True, paginate: bool = True):
    """
    Process a document file (PDF, DOCX, etc.) and return markdown text with metadata.
    
    Args:
        file_bytes (bytes): The document file content
        filename (str): The original filename (optional)
        model_dict: Pre-loaded model dictionary
        extract_images (bool): Whether to extract images
        paginate (bool): Whether to paginate the output based on original document pages
    
    Returns:
        dict: Processing results matching PDFConversionResult schema
    """
    try:
        # Determine file type from filename
        file_extension = os.path.splitext(filename)[1].lower() if filename else '.pdf'
        
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {file_extension}. Supported formats: {SUPPORTED_EXTENSIONS}")
        
        logger.info(f"Processing {file_extension} file: {filename}")
        
        full_text, images, processing_time, converted_pdf = parse_document_and_return_markdown(
            file_bytes, filename, extract_images, model_dict, paginate
        )
        
        # Convert metadata to match GeneralMetadata schema
        general_metadata = {
            "custom_metadata": {
                "processing_time": processing_time,
                "file_type": file_extension,
                "text_length": len(full_text) if isinstance(full_text, str) else sum(len(page) for page in full_text),
                "pages": len(full_text) if isinstance(full_text, list) else None
            },
            "converted_pdf_base64": converted_pdf
        }
        
        result = {
            "filename": filename or f"document{file_extension}",
            "markdown": full_text,  # This will be either a string or a list of strings depending on pagination
            "metadata": general_metadata,
            "images": images if extract_images else {},
            "status": "success"
        }
        
        logger.info(f"Successfully processed {filename}: {len(full_text)} chars, {len(images) if extract_images else 0} images")
        return result
        
    except Exception as e:
        logger.error(f"Error in process_document_file: {str(e)}")
        return {
            "filename": filename or "document.pdf",
            "markdown": "" if not paginate else [],
            "metadata": {
                "custom_metadata": {"error": str(e), "file_type": file_extension if filename else ".pdf"},
                "converted_pdf_base64": None
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
