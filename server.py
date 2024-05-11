import os
import argparse
from fastapi import FastAPI, UploadFile, File
from typing import List
from marker.convert import convert_single_pdf
from marker.logger import configure_logging
from marker.models import load_all_models
from marker.output import save_markdown

app = FastAPI()

def parse_pdf_and_return_markdown(pdf_file: bytes, filename: str, output_folder: str):
    model_lst = load_all_models()
    full_text, images, out_meta = convert_single_pdf(pdf_file, model_lst)
    subfolder_path = save_markdown(output_folder, filename, full_text, images, out_meta)
    return subfolder_path

@app.post("/convert")
async def convert_pdf_to_markdown(pdf_file: UploadFile = File(...)):
    if pdf_file.content_type != "application/pdf":
        return {"error": "Only PDF files are supported."}
    
    filename = pdf_file.filename
    output_folder = "output"  # Assuming output folder path
    
    subfolder_path = parse_pdf_and_return_markdown(await pdf_file.read(), filename, output_folder)
    return {"message": f"Markdown saved to {subfolder_path} folder"}

def main():
    # Load all models before starting the server
    configure_logging()  # Assuming this function initializes logging
    load_all_models()
    
    # Start the server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
