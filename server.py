import os
import argparse
import base64
from fastapi import FastAPI, UploadFile, File, status, HTTPException
from typing import List
from marker.convert import convert_single_pdf
from marker.logger import configure_logging
from marker.models import load_all_models
from marker.settings import Settings
# from marker.output import save_markdown

app = FastAPI()

model_list = load_all_models()

def parse_pdf_and_return_markdown(pdf_file: bytes , extract_images: bool):
    full_text, images, out_meta = convert_single_pdf(pdf_file, model_list)
    print(images)
    image_data = {}
    if extract_images:
        for i, (filename, image) in enumerate(images.items()):
            print(f"Processing image {filename}")
            
            # Save image as PNG
            image.save(filename, "PNG")

            # Read the saved image file as bytes
            with open(filename, "rb") as f:
                image_bytes = f.read()

            # Convert image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_data[f'{filename}'] = image_base64

            # Remove the temporary image file
            os.remove(filename)

    return full_text, out_meta, image_data

@app.get("/")
async def server():
    return {"Welcome to marker api server"}

@app.post("/convert")
async def convert_pdf_to_markdown(pdf_files: List[UploadFile] = File(...), extract_images: bool = True):
    if extract_images == False:
        Settings.EXTRACT_IMAGES = False
        print("EXTRACT_IMAGES set to False")
    else:
        Settings.EXTRACT_IMAGES = True

    results = []

    for pdf_file in pdf_files:
        if pdf_file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f'File {pdf_file.filename} has unsupported extension type',
            )
        markdown_text, metadata, image_data = parse_pdf_and_return_markdown(await pdf_file.read(), extract_images=extract_images)
        results.append({
            "filename": pdf_file.filename,
            "markdown": markdown_text,
            "metadata": metadata,
            "images": image_data,
        })

    return results

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the marker-api server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--workers", type=int, default=4, help="number of workers")
    args = parser.parse_args()

    # Load all models before starting the server
    configure_logging()  # Assuming this function initializes logging    

    # Start the server
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port , workers=args.workers)

if __name__ == "__main__":
    main()
