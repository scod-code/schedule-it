from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Tuple
from datetime import date, time, datetime


class Venue(BaseModel):
    name: str
    capacity: int = Field(default=100, ge=1)


class TimeSlot(BaseModel):
    date: date
    time: time
    venue_name: str


class ScheduleRequest(BaseModel):
    league_name: str = "My League"
    teams: List[str] = Field(..., min_length=4, max_length=32)
    venues: List[Venue]
    slots: List[TimeSlot]
    round_robin: Literal["single", "double"] = "single"
    blackout_dates: List[date] = Field(default_factory=list)
    max_consecutive_home: int = Field(default=3, ge=1, le=10)
    max_consecutive_away: int = Field(default=3, ge=1, le=10)
    derby_pairs: List[Tuple[str, str]] = Field(default_factory=list)
    derby_separation: int = Field(default=4, ge=1, le=20)

    @field_validator("teams")
    @classmethod
    def teams_unique(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Team names must be unique")
        return v


class Match(BaseModel):
    round_num: int
    date: date
    time: time
    home_team: str
    away_team: str
    venue: str
    venue_capacity: int


class QualityMetrics(BaseModel):
    violations: int
    home_away_breaks: int
    balance_score: float
    solve_time_ms: int
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "TIMEOUT"]


class ScheduleResult(BaseModel):
    matches: List[Match]
    metrics: QualityMetrics
    infeasibility_reason: Optional[str] = None
    total_rounds: int
    total_matches: int
