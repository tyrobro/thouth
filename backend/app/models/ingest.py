from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum


class ContentType(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    URL = "url"


class IngestTextRequest(BaseModel):
    text: str
    subject: Optional[str] = None
    title: Optional[str] = None


class IngestURLRequest(BaseModel):
    url: str
    subject: Optional[str] = None
    title: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    chunks_created: int
    source: str
    subject: Optional[str] = None
    message: str
