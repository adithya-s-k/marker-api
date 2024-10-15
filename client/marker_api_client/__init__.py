import aiohttp
import asyncio
import requests
from typing import List, Union, Dict, Any
from enum import Enum
from pydantic import BaseModel
from tqdm import tqdm
from tqdm.asyncio import tqdm as atqdm
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ServerType(str, Enum):
    simple = "simple"
    distributed = "distributed"


class HealthResponse(BaseModel):
    message: str
    type: ServerType
    workers: int = None


class ConversionResponse(BaseModel):
    status: str
    result: Dict[str, Any] = None


class CeleryTaskResponse(BaseModel):
    task_id: str
    status: str


class BatchConversionResponse(BaseModel):
    task_id: str
    status: str


class MarkerAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.server_type = None
        logger.info(f"Initializing MarkerAPIClient with base URL: {self.base_url}")

    async def __aenter__(self):
        self.async_session = aiohttp.ClientSession()
        await self.acheck_health()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.async_session.close()

    def __enter__(self):
        self.check_health()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def check_health(self):
        logger.info("Checking server health...")
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        health_data = HealthResponse(**response.json())
        self.server_type = health_data.type
        self._log_server_info(health_data)
        return health_data

    async def acheck_health(self):
        logger.info("Checking server health asynchronously...")
        async with self.async_session.get(f"{self.base_url}/health") as response:
            response.raise_for_status()
            health_data = HealthResponse(**(await response.json()))
            self.server_type = health_data.type
            self._log_server_info(health_data)
            return health_data

    def _log_server_info(self, health_data: HealthResponse):
        if health_data.type == ServerType.simple:
            logger.info("Connected to a simple server")
        else:
            logger.info(
                f"Connected to a distributed server with {health_data.workers} workers"
            )

    def _convert_endpoint(self):
        return (
            "/convert" if self.server_type == ServerType.simple else "/celery/convert"
        )

    def _batch_convert_endpoint(self):
        return "/batch_convert"

    def load_data(
        self, file_paths: Union[str, List[str]], show_progress: bool = False
    ) -> Union[ConversionResponse, BatchConversionResponse]:
        if isinstance(file_paths, str):
            logger.info(f"Converting single file: {file_paths}")
            return self._convert_single(file_paths)
        elif isinstance(file_paths, list):
            logger.info(f"Converting batch of {len(file_paths)} files")
            return self._convert_batch(file_paths, show_progress)
        else:
            raise ValueError("file_paths must be a string or a list of strings")

    def _convert_single(self, file_path: str) -> ConversionResponse:
        with open(file_path, "rb") as file:
            files = {"pdf_file": file}
            logger.info(f"Sending request to convert {file_path}")
            response = self.session.post(
                f"{self.base_url}{self._convert_endpoint()}", files=files
            )
        response.raise_for_status()
        logger.info(f"Successfully converted {file_path}")
        return ConversionResponse(**response.json())

    def _convert_batch(
        self, file_paths: List[str], show_progress: bool
    ) -> BatchConversionResponse:
        files = []
        iterable = tqdm(file_paths, desc="Preparing files", disable=not show_progress)
        for file_path in iterable:
            files.append(("pdf_files", open(file_path, "rb")))
            logger.info(f"Prepared file: {file_path}")

        logger.info("Sending batch conversion request")
        response = self.session.post(
            f"{self.base_url}{self._batch_convert_endpoint()}", files=files
        )
        response.raise_for_status()
        logger.info("Batch conversion request successful")
        return BatchConversionResponse(**response.json())

    async def aload_data(
        self, file_paths: Union[str, List[str]], show_progress: bool = False
    ) -> Union[ConversionResponse, BatchConversionResponse]:
        if isinstance(file_paths, str):
            logger.info(f"Converting single file asynchronously: {file_paths}")
            return await self._aconvert_single(file_paths)
        elif isinstance(file_paths, list):
            logger.info(f"Converting batch of {len(file_paths)} files asynchronously")
            return await self._aconvert_batch(file_paths, show_progress)
        else:
            raise ValueError("file_paths must be a string or a list of strings")

    async def _aconvert_single(self, file_path: str) -> ConversionResponse:
        data = aiohttp.FormData()
        data.add_field("pdf_file", open(file_path, "rb"))
        logger.info(f"Sending async request to convert {file_path}")
        async with self.async_session.post(
            f"{self.base_url}{self._convert_endpoint()}", data=data
        ) as response:
            response.raise_for_status()
            logger.info(f"Successfully converted {file_path} asynchronously")
            return ConversionResponse(**(await response.json()))

    async def _aconvert_batch(
        self, file_paths: List[str], show_progress: bool
    ) -> BatchConversionResponse:
        data = aiohttp.FormData()
        async for file_path in atqdm(
            file_paths, desc="Preparing files", disable=not show_progress
        ):
            data.add_field("pdf_files", open(file_path, "rb"))
            logger.info(f"Prepared file: {file_path}")

        logger.info("Sending async batch conversion request")
        async with self.async_session.post(
            f"{self.base_url}{self._batch_convert_endpoint()}", data=data
        ) as response:
            response.raise_for_status()
            logger.info("Async batch conversion request successful")
            return BatchConversionResponse(**(await response.json()))

    def get_result(self, task_id: str) -> ConversionResponse:
        if self.server_type != ServerType.distributed:
            raise ValueError("get_result is only available for distributed server type")
        logger.info(f"Getting result for task {task_id}")
        response = self.session.get(f"{self.base_url}/celery/result/{task_id}")
        response.raise_for_status()
        logger.info(f"Successfully retrieved result for task {task_id}")
        return ConversionResponse(**response.json())

    async def aget_result(self, task_id: str) -> ConversionResponse:
        if self.server_type != ServerType.distributed:
            raise ValueError(
                "aget_result is only available for distributed server type"
            )
        logger.info(f"Getting result asynchronously for task {task_id}")
        async with self.async_session.get(
            f"{self.base_url}/celery/result/{task_id}"
        ) as response:
            response.raise_for_status()
            logger.info(
                f"Successfully retrieved result asynchronously for task {task_id}"
            )
            return ConversionResponse(**(await response.json()))

    def get_batch_result(self, task_id: str) -> BatchConversionResponse:
        if self.server_type != ServerType.distributed:
            raise ValueError(
                "get_batch_result is only available for distributed server type"
            )
        logger.info(f"Getting batch result for task {task_id}")
        response = self.session.get(f"{self.base_url}/batch_convert/result/{task_id}")
        response.raise_for_status()
        logger.info(f"Successfully retrieved batch result for task {task_id}")
        return BatchConversionResponse(**response.json())

    async def aget_batch_result(self, task_id: str) -> BatchConversionResponse:
        if self.server_type != ServerType.distributed:
            raise ValueError(
                "aget_batch_result is only available for distributed server type"
            )
        logger.info(f"Getting batch result asynchronously for task {task_id}")
        async with self.async_session.get(
            f"{self.base_url}/batch_convert/result/{task_id}"
        ) as response:
            response.raise_for_status()
            logger.info(
                f"Successfully retrieved batch result asynchronously for task {task_id}"
            )
            return BatchConversionResponse(**(await response.json()))


# Example usage:
async def main():
    async with MarkerAPIClient("http://localhost:8080") as client:
        # Synchronous batch conversion with progress
        batch_result = client.load_data(
            ["./file1.pdf", "./file2.pdf", "./file3.pdf"], show_progress=True
        )
        print(batch_result)

        # Asynchronous batch conversion with progress
        async_batch_result = await client.aload_data(
            ["./file1.pdf", "./file2.pdf", "./file3.pdf"], show_progress=True
        )
        print(async_batch_result)


if __name__ == "__main__":
    asyncio.run(main())
