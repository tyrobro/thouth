from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import httpx
from bs4 import BeautifulSoup
import tempfile
import os
import logging
from typing import List
from enum import Enum

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


class ContentType(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    URL = "url"


def get_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    )


def ingest_text(text: str, metadata: dict = {}) -> List[Document]:
    doc = Document(page_content=text, metadata=metadata)
    splitter = get_splitter()
    chunks = splitter.split_documents([doc])
    logger.info(f"Text ingested: {len(chunks)} chunks from {len(text)} chars")
    return chunks


def ingest_pdf(file_bytes: bytes, filename: str, metadata: dict = {}) -> List[Document]:
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_bytes))
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(Document(
                page_content=text,
                metadata={
                    "source": filename,
                    "type": ContentType.PDF,
                    "page": i,
                    **metadata
                }
            ))

    splitter = get_splitter()
    chunks = splitter.split_documents(docs)
    logger.info(f"PDF ingested: {len(chunks)} chunks from {len(docs)} pages — {filename}")
    return chunks


def ingest_url(url: str, metadata: dict = {}) -> List[Document]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Thouth/1.0)"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    # Remove nav, footer, scripts, styles
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    doc = Document(
        page_content=text,
        metadata={
            "source": url,
            "type": ContentType.URL,
            "title": soup.title.string if soup.title else url,
            **metadata
        }
    )

    splitter = get_splitter()
    chunks = splitter.split_documents([doc])
    logger.info(f"URL ingested: {len(chunks)} chunks from {url}")
    return chunks
