"""Intelligent HTSUS classification endpoints."""
from fastapi import APIRouter

from app.classification_schemas import (
    ClassificationResult,
    ProductClassificationRequest,
    RagIndexStatus,
)
from app.rag import ClassificationService, RagIndex
from app.schemas import Envelope

router = APIRouter(prefix="/api/classify", tags=["classification"])
_index = RagIndex()
_service = ClassificationService(index=_index)


@router.get("/index-status", response_model=Envelope[RagIndexStatus])
def index_status() -> Envelope[RagIndexStatus]:
    return Envelope(data=RagIndexStatus(**_index.status()))


@router.post("", response_model=Envelope[ClassificationResult])
def classify_product(
    body: ProductClassificationRequest,
) -> Envelope[ClassificationResult]:
    result = _service.classify(body.model_dump())
    return Envelope(data=ClassificationResult(**result))
