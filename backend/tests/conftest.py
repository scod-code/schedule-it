import pytest
from datetime import date, time, timedelta
from fastapi.testclient import TestClient
from app.models import ScheduleRequest, Venue, TimeSlot
from app.main import app


def make_slots(n_slots: int, start_date_str: str = "2025-06-01", venue_name: str = "Stadium") -> list:
    """Generate n_slots slots on consecutive days."""
    slots = []
    base = date.fromisoformat(start_date_str)
    for i in range(n_slots):
        slots.append(TimeSlot(
            date=base + timedelta(days=i),
            time=time(15, 0),
            venue_name=venue_name
        ))
    return slots


@pytest.fixture
def four_team_request():
    # 4 teams, single RR needs 6 matches minimum
    return ScheduleRequest(
        league_name="Test League",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )


@pytest.fixture
def six_team_request():
    # 6 teams, single RR needs 15 matches
    teams = [f"Team {i}" for i in range(1, 7)]
    return ScheduleRequest(
        league_name="Six Team League",
        teams=teams,
        venues=[Venue(name="Ground", capacity=200)],
        slots=make_slots(20),
        round_robin="single",
    )


@pytest.fixture
def client():
    return TestClient(app)
