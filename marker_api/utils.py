import base64
import torch
from enum import Enum
import pynvml
import io
from art import text2art
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    CPU = "cpu"
    GPU = "gpu"


def process_image_to_base64(image: Image.Image, filename: str) -> str:
    """
    Process an image and convert it to base64.

    Args:
    image (PIL.Image.Image): The image to process.
    filename (str): The filename to use for the temporary file.

    Returns:
    str: The base64 encoded string of the image.
    """
    try:
        # Save image as PNG in memory
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        # Convert image to base64
        image_base64 = base64.b64encode(img_byte_arr).decode("utf-8")

        return image_base64
    except Exception as e:
        logger.error(f"Error processing image {filename}: {str(e)}")
        return ""


def get_ram_available():
    """
    Function to get VRAM/RAM availability on device

    Used to set the number of workers

    """

    if torch.cuda.is_available():
        # Initialize NVML to access GPU memory info
        pynvml.nvmlInit()

        # Get handle for the first GPU
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        # Get memory info
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

        # Calculate available VRAM in MB
        ram_available = mem_info.free // (1024**2)  # Convert bytes to MB

        # Cleanup NVML
        pynvml.nvmlShutdown()

        return DeviceType.GPU, ram_available

    else:
        # For CPU, use torch's built-in method to get total RAM available
        ram_available = torch.cuda.memory_reserved() // (1024**2)  # Convert bytes to MB
        return DeviceType.CPU, ram_available


# # Example usage:
# device_type, ram_available = get_ram_available()
# print(f"Device Type: {device_type}, Available RAM: {ram_available} MB")


def print_markerapi_text_art(suffix=None):
    font = "nancyj"
    ascii_text = "Marker-api"
    if suffix:
        ascii_text += f"  x  {suffix}"
    ascii_art = text2art(ascii_text, font=font)
    print("\n")
    print(ascii_art)
    print(
        """Easily deployable and highly Scalable 🚀 API to convert PDF to markdown quickly with high accuracy."""
    )
    print("""Abstracted by Adithya S K : https://twitter.com/adithya_s_k""")
    print("\n")
    print("\n")
