import os
import random
import time
from locust import HttpUser, between, task
import logging

logger = logging.getLogger(__name__)

PORT = 8080
HOST = f"http://fastapi:{PORT}"

PDF_DIR = "./data"


def load_pdf_files():
    logger.info("Loading PDF files...")
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    logger.info(f"Loaded {len(pdf_files)} PDF files.")
    return pdf_files


PDF_FILES = load_pdf_files()


class PDFConversionLoadTest(HttpUser):
    """Locust load test for PDF Conversion API."""

    host = HOST
    wait_time = between(1, 5)

    def convert_pdf(self):
        """Send a PDF conversion request to the API."""
        endpoint = "/convert"
        headers = {"Content-Type": "multipart/form-data"}
        request_count = 0

        # Select a random PDF file
        pdf_file = random.choice(PDF_FILES)
        pdf_path = os.path.join(PDF_DIR, pdf_file)

        with open(pdf_path, "rb") as file:
            files = {"pdf_file": (pdf_file, file, "application/pdf")}
            resp = self.client.post(endpoint, headers=headers, files=files)

        if resp.status_code not in (200, 202):
            logger.error(f"Request failed: {resp.text}")
            return
        request_count += 1
        resp_data = resp.json()

        # Check if the response contains the result directly
        if "result" in resp_data and resp_data["status"] == "Success":
            logger.info("Task completed immediately.")
            return

        # If not, we need to poll for the result
        task_id = resp_data.get("task_id")
        if not task_id:
            logger.error("No task_id in response")
            return

        time.sleep(2)
        result_endpoint = f"/celery/result/{task_id}"

        while True:
            resp = self.client.get(result_endpoint)
            request_count += 1
            resp_data = resp.json()
            status = resp_data.get("status")

            if status == "Success":
                logger.info("Task completed.")
                break
            elif status != "Processing":
                logger.error(f"Unexpected status: {status}")
                break

            time.sleep(5)

        logger.info(f"Request count: {request_count}")

    @task
    def execute_task(self):
        """Execute PDF conversion task."""
        self.convert_pdf()


if __name__ == "__main__":
    PDFConversionLoadTest.host = HOST
