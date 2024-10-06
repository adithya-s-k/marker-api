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

    for pdf in response_data:
        pdf_filename = pdf['filename']
        pdf_output_folder = os.path.join(output_folder, os.path.splitext(pdf_filename)[0])

        # Create a folder for each PDF
        os.makedirs(pdf_output_folder, exist_ok=True)

        # Save markdown
        markdown_text = pdf['markdown']
        with open(os.path.join(pdf_output_folder, 'output.md'), 'w', encoding='utf-8') as f:
            f.write(markdown_text)

        # Save images
        image_data = pdf['images']
        for image_name, image_base64 in image_data.items():
            # Decode base64 image
            image_bytes = base64.b64decode(image_base64)

            # Save image
            with open(os.path.join(pdf_output_folder, image_name), 'wb') as f:
                f.write(image_bytes)

def convert_pdf_to_markdown_and_save(pdf_file_paths, output_folder, server_url):
    files = []
    
    # Prepare the files for the request
    for pdf_file_path in pdf_file_paths:
        with open(pdf_file_path, 'rb') as f:
            pdf_content = f.read()
        files.append(('pdf_files', (os.path.basename(pdf_file_path), pdf_content, 'application/pdf')))
        
    # Send request to FastAPI server with all PDF files attached
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
    parser.add_argument('--server_url', type=str, required=True, help='URL of the server for PDF conversion')
    parser.add_argument('--filename', type=str, nargs='+', required=True, help='Paths to the PDF files')
    parser.add_argument('--output', type=str, required=True, help='Output folder for saving markdown and images')
    args = parser.parse_args()

    # Convert PDF to markdown and save
    convert_pdf_to_markdown_and_save(args.filename, args.output, args.server_url)

    """
    python invoke.py --server_url http://127.0.0.1:8000/convert --filename test1.pdf test2.pdf --output output
    """