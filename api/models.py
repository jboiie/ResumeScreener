"""
Pydantic models for request validation and response serialization.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Models ─────────────────────────────────────────────────────────────

class ScreeningFilters(BaseModel):
    """Optional filters to narrow down candidates."""

    min_experience: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum years of experience required",
    )
    location: Optional[str] = Field(
        None,
        description="Preferred candidate location (matched semantically by the LLM)",
    )


class ScreeningRequest(BaseModel):
    """Body for POST /api/v1/screen"""

    job_description: str = Field(
        ...,
        min_length=20,
        description="Full text of the job description to screen against",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of top candidates to return (max 50)",
    )
    filters: ScreeningFilters = Field(
        default_factory=ScreeningFilters,
        description="Optional filters (handled by LLM reranker)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI, PostgreSQL, and Docker. Experience with machine learning pipelines is a plus.",
                    "top_k": 10,
                    "filters": {
                        "min_experience": 5,
                        "location": "Delhi",
                    },
                }
            ]
        }
    }


# ── Response Models ────────────────────────────────────────────────────────────

class Candidate(BaseModel):
    """A single ranked candidate."""

    candidate_id: str = Field(description="Unique identifier for this candidate")
    name: str = Field(description="Candidate's name extracted from their CV")
    score: float = Field(ge=0.0, le=1.0, description="Fit score between 0.0 and 1.0")
    match_reasoning: str = Field(description="One-sentence explanation of why this candidate fits")
    cv_path: str = Field(description="Path to the candidate's CV file on the server")


class ScreeningResponse(BaseModel):
    """Response from POST /api/v1/screen"""

    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this screening request (for logging/tracking)",
    )
    candidates: list[Candidate] = Field(description="Ranked list of top candidates")
    screened_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of when screening was performed",
    )


class HealthResponse(BaseModel):
    """Response from GET /health"""

    status: str = Field(description="'healthy' or 'degraded'")
    qdrant_connected: bool = Field(description="Whether the vector database is reachable")
    model_loaded: bool = Field(description="Whether the embedding model is loaded in memory")
    version: str = Field(default="1.0.0", description="API version")
