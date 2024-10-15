import os
import random
import time
from locust import HttpUser, between, task
import logging

logger = logging.getLogger(__name__)

PORT = 8080
HOST = f"http://51.8.81.159:8080"

PDF_DIR = "./data"


def load_pdf_files():
    logger.info("Loading PDF files...")
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

    # Print the loaded PDF files
    print(f"Loaded the following PDF files: {pdf_files}")

    logger.info(f"Loaded {len(pdf_files)} PDF files.")
    return pdf_files


PDF_FILES = load_pdf_files()


class PDFConversionLoadTest(HttpUser):
    """Locust load test for PDF Conversion API."""

    host = HOST
    wait_time = between(1, 5)

    def convert_pdf(self, endpoint):
        """Send a PDF conversion request to the specified API endpoint."""
        headers = {"Content-Type": "multipart/form-data"}
        request_count = 0

        # Select a random PDF file
        pdf_file = random.choice(PDF_FILES)
        pdf_path = os.path.join(PDF_DIR, pdf_file)

        # Open the file outside the `with` block to keep it open during the request
        file = open(pdf_path, "rb")
        files = {"pdf_file": (pdf_file, file, "application/pdf")}

        try:
            resp = self.client.post(endpoint, headers=headers, files=files)
            if resp.status_code not in (200, 202):
                logger.error(f"Request failed: {resp.text}")
                return
            request_count += 1
            resp_data = resp.json()

            # Check if the response contains the result directly
            if "result" in resp_data and resp_data.get("status") == "Success":
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

        finally:
            # Ensure the file is closed after the request completes
            file.close()

        logger.info(f"Request count: {request_count}")

    @task(3)
    def convert_endpoint(self):
        """Execute PDF conversion task using /convert endpoint."""
        self.convert_pdf("/convert")

    @task(3)
    def celery_convert_endpoint(self):
        """Execute PDF conversion task using /celery/convert endpoint."""
        self.convert_pdf("/celery/convert")

    @task(1)
    def batch_convert_endpoint(self):
        """Execute batch PDF conversion task using /batch endpoint."""
        endpoint = "/batch"
        headers = {"Content-Type": "multipart/form-data"}
        request_count = 0

        # Select multiple random PDF files (3 in this case)
        pdf_files = random.sample(PDF_FILES, 3)
        files = []
        for pdf_file in pdf_files:
            pdf_path = os.path.join(PDF_DIR, pdf_file)
            with open(pdf_path, "rb") as file:
                files.append(("pdf_files", (pdf_file, file, "application/pdf")))

        resp = self.client.post(endpoint, headers=headers, files=files)

        if resp.status_code not in (200, 202):
            logger.error(f"Batch request failed: {resp.text}")
            return
        request_count += 1
        resp_data = resp.json()

        task_id = resp_data.get("task_id")
        if not task_id:
            logger.error("No task_id in batch response")
            return

        time.sleep(2)
        result_endpoint = f"/batch/result/{task_id}"

        while True:
            resp = self.client.get(result_endpoint)
            request_count += 1
            resp_data = resp.json()
            status = resp_data.get("status")

            if status == "Success":
                logger.info("Batch task completed.")
                break
            elif status != "Processing":
                logger.error(f"Unexpected batch status: {status}")
                break

            time.sleep(5)

        logger.info(f"Batch request count: {request_count}")


if __name__ == "__main__":
    PDFConversionLoadTest.host = HOST
