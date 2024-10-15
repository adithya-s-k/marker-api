from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Type, Union, Any
from enum import Enum


# Pydantic models for request/response schemas
class ServerType(str, Enum):
    simple = "simple"
    distributed = "distributed"


class HealthResponse(BaseModel):
    message: str
    type: ServerType
    workers: Optional[int] = Field(
        None, description="Number of workers (only for distributed type)"
    )

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type["HealthResponse"]) -> None:
            schema["anyOf"] = [
                {
                    "properties": {
                        "type": {"enum": ["simple"]},
                        "workers": {"type": "null"},
                    }
                },
                {
                    "properties": {
                        "type": {"enum": ["distributed"]},
                        "workers": {"type": "integer"},
                    },
                    "required": ["workers"],
                },
            ]


class GeneralMetadata(BaseModel):
    languages: Optional[Union[str, List[str]]] = None
    toc: Optional[List[Dict[str, Any]]] = None
    pages: Optional[int] = None
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class PDFConversionResult(BaseModel):
    filename: str
    markdown: str
    metadata: GeneralMetadata
    images: Dict[str, str]
    status: str


class ConversionResponse(BaseModel):
    status: str
    result: Optional[PDFConversionResult] = None


class CeleryTaskResponse(BaseModel):
    task_id: str
    status: str


class CeleryResultResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[PDFConversionResult] = None


class BatchConversionResponse(BaseModel):
    task_id: str
    status: str


class BatchResultResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[List[PDFConversionResult]] = None
    completed: Optional[int] = None
    total: Optional[int] = None
    progress: Optional[str] = None
