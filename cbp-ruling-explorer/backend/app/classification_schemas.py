"""Request and response models for intelligent HTSUS classification."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProductClassificationRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=300)
    product_type: str = Field(default="", max_length=300)
    description: str = ""
    materials: list[str] = Field(default_factory=list, max_length=50)
    components: list[str] = Field(default_factory=list, max_length=50)
    functions: list[str] = Field(default_factory=list, max_length=50)
    intended_use: str = Field(default="", max_length=2000)
    technical_specs: str = Field(default="", max_length=4000)
    country_of_origin: str = Field(default="", max_length=200)

    @field_validator("materials", "components", "functions")
    @classmethod
    def _clean_list(cls, value: list[str]) -> list[str]:
        return [item.strip()[:300] for item in value if item.strip()]


class ClassificationPrimary(BaseModel):
    hts_code: str
    description: str
    parent_path: str = ""
    confidence: Literal["high", "medium", "low"]
    basis: list[str] = Field(default_factory=list)


class ClassificationAlternative(BaseModel):
    hts_code: str
    description: str
    reason: str


class CaseReference(BaseModel):
    ruling_no: str
    subject: str
    ruling_date: str = ""
    year: int = 0
    hs_codes: list[str] = Field(default_factory=list)
    status: str
    detail_url: str
    section: str
    excerpt: str
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    product_profile: str
    primary: ClassificationPrimary | None = None
    alternatives: list[ClassificationAlternative] = Field(default_factory=list)
    references: list[CaseReference] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    hts_version: str = ""
    disclaimer: str


class RagIndexStatus(BaseModel):
    ready: bool
    chunks: int
    rulings: int
    hts_entries: int
    hts_version: str
