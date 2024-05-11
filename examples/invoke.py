import os
import requests
from PIL import Image
import base64
import argparse

"""
python invoke.py --server_url http://127.0.0.1:8000/convert --filename test.pdf --output output
"""

def save_images_and_markdown(response_data, output_folder):
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Save markdown
    markdown_text = response_data['markdown']
    with open(os.path.join(output_folder, 'output.md'), 'w', encoding='utf-8') as f:
        f.write(markdown_text)

    # Save images
    image_data = response_data['images']
    for image_name, image_base64 in image_data.items():
        # Decode base64 image
        image_bytes = base64.b64decode(image_base64)

        # Save image
        with open(os.path.join(output_folder, f'{image_name}.png'), 'wb') as f:
            f.write(image_bytes)

def convert_pdf_to_markdown_and_save(pdf_file_path, output_folder, server_url):
    # Open PDF file in binary mode
    with open(pdf_file_path, 'rb') as f:
        pdf_content = f.read()
        
    # Send request to FastAPI server with PDF file attached
    files = {'pdf_file': (os.path.basename(pdf_file_path), pdf_content, 'application/pdf')}
    response = requests.post(server_url, files=files)

    # Check if request was successful
    if response.status_code == 200:
        # Save markdown and images
        response_data = response.json()
        save_images_and_markdown(response_data, output_folder)
        print("Markdown and images saved successfully.")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description='Convert PDF to markdown and save.')
    parser.add_argument('--server_url', type=str, help='URL of the server for PDF conversion')
    parser.add_argument('--filename', type=str, help='Path to the PDF file')
    parser.add_argument('--output', type=str, help='Output folder for saving markdown and images')
    args = parser.parse_args()

    # Convert PDF to markdown and save
    convert_pdf_to_markdown_and_save(args.filename, args.output, args.server_url)


    """
    python invoke.py --server_url http://127.0.0.1:8000/convert --filename test.pdf --output output
    """