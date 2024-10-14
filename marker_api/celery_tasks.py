from celery import Task
from marker_api.celery_worker import celery_app
from marker.convert import convert_single_pdf
from marker.models import load_all_models
import io
import logging
from marker_api.utils import process_image_to_base64

logger = logging.getLogger(__name__)


class PDFConversionTask(Task):
    abstract = True

    def __init__(self):
        super().__init__()
        self.model_list = None

    def __call__(self, *args, **kwargs):
        if not self.model_list:
            self.model_list = load_all_models()
        return self.run(*args, **kwargs)


@celery_app.task(
    ignore_result=False, bind=True, base=PDFConversionTask, name="convert_pdf"
)
def convert_pdf_to_markdown(self, filename, pdf_content):
    pdf_file = io.BytesIO(pdf_content)
    markdown_text, images, metadata = convert_single_pdf(pdf_file, self.model_list)
    image_data = {}
    for i, (img_filename, image) in enumerate(images.items()):
        logger.debug(f"Processing image {img_filename}")
        image_base64 = process_image_to_base64(image, img_filename)
        image_data[img_filename] = image_base64

    return {
        "filename": filename,
        "markdown": markdown_text,
        "metadata": metadata,
        "images": image_data,
        "status": "ok",
    }
