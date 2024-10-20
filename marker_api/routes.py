import os
import time
import base64
from marker.convert import convert_single_pdf
from marker.logger import configure_logging
import logging

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)


# Function to parse PDF and return markdown, metadata, and image data
def parse_pdf_and_return_markdown(pdf_file: bytes, extract_images: bool, model_list, **kwargs):
    """
    Function to parse a PDF and extract text and images.

    Args:
    pdf_file (bytes): The content of the PDF file.
    extract_images (bool): Whether to extract images or not.

    Returns
    tuple: A tuple containing the full text, metadata, and image data (if extracted).
    """
    logger.debug("Parsing PDF file")
    full_text, images, out_meta = convert_single_pdf(pdf_file, model_list, **kwargs)
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
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            image_data[f"{filename}"] = image_base64

            # Remove the temporary image file
            os.remove(filename)

    return full_text, out_meta, image_data


# Function to process a single PDF file
def process_pdf_file(file_content: bytes, filename: str, model_list, **kwargs):
    """
    Function to process a single PDF file.

    Args:
    file_content (bytes): The content of the PDF file.
    filename (str): The name of the PDF file.
    model_list: The list of loaded models.

    Returns:
    dict: A dictionary containing the filename, markdown text, metadata, image data, status, and processing time.
    """
    entry_time = time.time()
    logger.info(f"Entry time for {filename}: {entry_time}")
    markdown_text, metadata, image_data = parse_pdf_and_return_markdown(
        file_content, extract_images=True, model_list=model_list, **kwargs
    )
    completion_time = time.time()
    logger.info(f"Model processes complete time for {filename}: {completion_time}")
    time_difference = completion_time - entry_time
    return {
        "filename": filename,
        "markdown": markdown_text,
        "metadata": metadata,
        "images": image_data,
        "status": "ok",
        "time": time_difference,
    }
