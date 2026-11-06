"""
Pydantic models for request / response validation.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class RoundRobinType(str, Enum):
    single = "single"
    double = "double"


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class Team(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    home_venue: str = Field(..., min_length=1, max_length=80)
    # Dates this team cannot play (ISO format strings, e.g. "2025-09-06")
    blackout_dates: List[str] = Field(default_factory=list)


class Venue(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    # Maximum simultaneous matches at this venue per slot
    capacity: int = Field(default=1, ge=1, le=10)


class TimeSlot(BaseModel):
    """A named playing slot, e.g. 'Saturday 10:00'."""
    label: str = Field(..., min_length=1, max_length=80)
    date: str = Field(..., description="ISO date for this slot, e.g. '2025-09-06'")


class ScheduleRequest(BaseModel):
    league_name: str = Field(..., min_length=1, max_length=120)
    teams: List[Team] = Field(..., min_length=2, max_length=40)
    venues: List[Venue] = Field(..., min_length=1, max_length=20)
    slots: List[TimeSlot] = Field(..., min_length=1)
    round_robin: RoundRobinType = RoundRobinType.single
    # Maximum consecutive home OR away games for any team
    max_consecutive_home_away: int = Field(default=3, ge=1, le=10)
    # Minimum slots between matches for "derby" pairs (team index pairs)
    derby_pairs: List[List[int]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_enough_slots(self) -> "ScheduleRequest":
        n = len(self.teams)
        matches_needed = n * (n - 1) // 2
        if self.round_robin == RoundRobinType.double:
            matches_needed *= 2
        if len(self.slots) < matches_needed:
            # Warn but don't hard-block — solver will report infeasibility
            pass
        return self


# ---------------------------------------------------------------------------
# Output / job models
# ---------------------------------------------------------------------------

class MatchResult(BaseModel):
    home_team: str
    away_team: str
    venue: str
    slot_label: str
    slot_date: str


class QualityMetrics(BaseModel):
    feasible: bool
    violations: int = 0
    home_away_breaks: int = 0
    balance_score: float = 0.0   # 0 = perfect balance, higher = worse
    solve_time_seconds: float = 0.0


class ScheduleResult(BaseModel):
    job_id: str
    league_name: str
    matches: List[MatchResult] = Field(default_factory=list)
    metrics: QualityMetrics
    paid: bool = False


class JobStatus(str, Enum):
    pending = "pending"
    solved = "solved"
    impossible = "impossible"
    paid = "paid"
    error = "error"


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.pending
    request: Optional[ScheduleRequest] = None
    result: Optional[ScheduleResult] = None
    stripe_session_id: Optional[str] = None
    created_at: str = ""           # ISO datetime string
    paid_at: Optional[str] = None  # ISO datetime string
