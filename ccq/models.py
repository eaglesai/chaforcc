"""Data models used by the ccq CLI."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class EarnRate(BaseModel):
    description: str
    value: Optional[str] = None


class InsuranceItem(BaseModel):
    name: str
    description: Optional[str] = None


class EligibilityRequirement(BaseModel):
    name: str
    detail: Optional[str] = None


class FeeItem(BaseModel):
    name: str
    amount: Optional[str] = None


class CardSchema(BaseModel):
    schema_version: str = Field("CardSchema v1", const=True)
    issuer: str
    card_name: str
    country: str
    network: Optional[str] = None
    card_type: Optional[str] = None
    annual_fee: Optional[float] = None
    purchase_apr: Optional[float] = Field(None, ge=0, le=99)
    cash_advance_apr: Optional[float] = Field(None, ge=0, le=99)
    fx_fee_percent: Optional[float] = Field(None, ge=0, le=50)
    grace_period_days: Optional[int] = Field(None, ge=0, le=120)
    signup_bonus: Optional[str] = None
    earn_rates: List[EarnRate] = Field(default_factory=list)
    insurance: List[InsuranceItem] = Field(default_factory=list)
    eligibility: List[EligibilityRequirement] = Field(default_factory=list)
    other_fees: List[FeeItem] = Field(default_factory=list)
    source_url: str
    source_type: str
    content_hash: str
    verified_at: Optional[datetime] = None
    extraction_notes: Optional[str] = None

    class Config:
        anystr_strip_whitespace = True
        validate_assignment = True

    @validator("content_hash")
    def _validate_hash(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("content_hash must be a SHA256 hex digest")
        return value


class VerificationResult(BaseModel):
    card_key: str
    issuer: str
    card_name: str
    status: str
    details: Dict[str, Any]
    source_path: Optional[str] = None


class DiffResult(BaseModel):
    card_key: str
    issuer: str
    card_name: str
    change_type: str
    current_hash: Optional[str] = None
    supabase_hash: Optional[str] = None
    changes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PublishRun(BaseModel):
    run_id: str
    total_cards: int
    published_cards: int
    skipped_cards: int
    failed_cards: int
    report_path: str
    created_at: datetime
