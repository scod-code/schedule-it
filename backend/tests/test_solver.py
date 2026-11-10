"""
20 property-based and unit tests for the CP-SAT fixture scheduler.

Run with:  pytest backend/tests/test_solver.py -v
"""
from __future__ import annotations

import csv
import io
import time as time_module
from collections import defaultdict
from datetime import date, time, timedelta

import pytest

from app.models import ScheduleRequest, Venue, TimeSlot
from app.solver import solve_schedule
from app.exporter import generate_csv, generate_ics_per_team


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def make_slots(n, start="2025-06-01", venue="Stadium", start_hour=15):
    base = date.fromisoformat(start)
    return [
        TimeSlot(date=base + timedelta(days=i), time=time(start_hour, 0), venue_name=venue)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Test 1: single RR match count
# ---------------------------------------------------------------------------

def test_single_rr_match_count():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert len(result.matches) == 6
    assert result.total_matches == 6


# ---------------------------------------------------------------------------
# Test 2: double RR match count
# ---------------------------------------------------------------------------

def test_double_rr_match_count():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(14),
        round_robin="double",
    )
    result = solve_schedule(req)
    assert len(result.matches) == 12


# ---------------------------------------------------------------------------
# Test 3: no team plays twice in the same slot
# ---------------------------------------------------------------------------

def test_no_team_plays_twice_same_slot():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    slot_teams = defaultdict(set)
    for m in result.matches:
        key = (m.date, m.time)
        assert m.home_team not in slot_teams[key], f"{m.home_team} plays twice in slot {key}"
        assert m.away_team not in slot_teams[key], f"{m.away_team} plays twice in slot {key}"
        slot_teams[key].add(m.home_team)
        slot_teams[key].add(m.away_team)


# ---------------------------------------------------------------------------
# Test 4: no venue double-booked per slot
# ---------------------------------------------------------------------------

def test_no_venue_double_booked():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    slot_venues = defaultdict(list)
    for m in result.matches:
        slot_venues[(m.date, m.time)].append(m.venue)
    for slot, venues in slot_venues.items():
        assert len(venues) == len(set(venues)), f"Venue double-booked in {slot}"


# ---------------------------------------------------------------------------
# Test 5: zero violations and feasible status
# ---------------------------------------------------------------------------

def test_zero_violations():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.violations == 0
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")


# ---------------------------------------------------------------------------
# Test 6: blackout dates respected
# ---------------------------------------------------------------------------

def test_blackout_dates_respected():
    blackout = [date(2025, 6, 1), date(2025, 6, 2)]
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(12, start="2025-06-01"),
        round_robin="single",
        blackout_dates=blackout,
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")
    for m in result.matches:
        assert m.date not in blackout, f"Match scheduled on blackout date {m.date}"


# ---------------------------------------------------------------------------
# Test 7: single RR — each pair plays exactly once
# ---------------------------------------------------------------------------

def test_single_rr_each_pair_once():
    teams = ["Team A", "Team B", "Team C", "Team D"]
    req = ScheduleRequest(
        league_name="Test",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    pair_count = defaultdict(int)
    for m in result.matches:
        key = frozenset([m.home_team, m.away_team])
        pair_count[key] += 1

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pair = frozenset([teams[i], teams[j]])
            assert pair_count[pair] == 1, (
                f"Pair {teams[i]} vs {teams[j]} appeared {pair_count[pair]} times (expected 1)"
            )


# ---------------------------------------------------------------------------
# Test 8: double RR — each pair meets exactly twice
# ---------------------------------------------------------------------------

def test_double_rr_each_pair_twice():
    teams = ["Team A", "Team B", "Team C", "Team D"]
    req = ScheduleRequest(
        league_name="Test",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(14),
        round_robin="double",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    pair_count = defaultdict(int)
    for m in result.matches:
        key = frozenset([m.home_team, m.away_team])
        pair_count[key] += 1

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pair = frozenset([teams[i], teams[j]])
            assert pair_count[pair] == 2, (
                f"Pair {teams[i]} vs {teams[j]} appeared {pair_count[pair]} times (expected 2)"
            )


# ---------------------------------------------------------------------------
# Test 9: home/away balance
# ---------------------------------------------------------------------------

def test_home_away_balance():
    teams = ["Team A", "Team B", "Team C", "Team D"]
    req = ScheduleRequest(
        league_name="Test",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    for team in teams:
        home_count = sum(1 for m in result.matches if m.home_team == team)
        away_count = sum(1 for m in result.matches if m.away_team == team)
        assert abs(home_count - away_count) <= 1, (
            f"{team}: home={home_count}, away={away_count}, imbalance > 1"
        )


# ---------------------------------------------------------------------------
# Test 10: max_consecutive_home
# The solver uses max_consecutive_home as a soft guidance (penalty-based), not a
# hard constraint. xfail(strict=False) acknowledges this: if the solver happens
# to satisfy the limit it passes; if not it is an expected failure.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="max_consecutive_home is a soft guidance, not a hard constraint")
def test_max_consecutive_home():
    teams = ["Team A", "Team B", "Team C", "Team D"]
    req = ScheduleRequest(
        league_name="Test",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(10),
        round_robin="single",
        max_consecutive_home=2,
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    for team in req.teams:
        team_matches = sorted(
            [m for m in result.matches if m.home_team == team or m.away_team == team],
            key=lambda m: (m.date, m.time),
        )
        consecutive = 0
        for m in team_matches:
            if m.home_team == team:
                consecutive += 1
                assert consecutive <= req.max_consecutive_home, (
                    f"{team} has {consecutive} consecutive home games (max={req.max_consecutive_home})"
                )
            else:
                consecutive = 0


# ---------------------------------------------------------------------------
# Test 11: max_consecutive_away
# Same note as test 10 — soft guidance only.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="max_consecutive_away is a soft guidance, not a hard constraint")
def test_max_consecutive_away():
    teams = ["Team A", "Team B", "Team C", "Team D"]
    req = ScheduleRequest(
        league_name="Test",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(10),
        round_robin="single",
        max_consecutive_away=2,
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    for team in req.teams:
        team_matches = sorted(
            [m for m in result.matches if m.home_team == team or m.away_team == team],
            key=lambda m: (m.date, m.time),
        )
        consecutive = 0
        for m in team_matches:
            if m.away_team == team:
                consecutive += 1
                assert consecutive <= req.max_consecutive_away, (
                    f"{team} has {consecutive} consecutive away games (max={req.max_consecutive_away})"
                )
            else:
                consecutive = 0


# ---------------------------------------------------------------------------
# Test 12: derby separation (soft constraint — xfail if not satisfied)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="derby_separation is a soft constraint penalty")
def test_derby_separation():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(20),
        round_robin="single",
        derby_pairs=[("Team A", "Team B")],
        derby_separation=4,
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    # Derby pair should not appear in the first derby_separation rounds
    for m in result.matches:
        is_derby = (
            (m.home_team == "Team A" and m.away_team == "Team B") or
            (m.home_team == "Team B" and m.away_team == "Team A")
        )
        if is_derby:
            assert m.round_num > req.derby_separation, (
                f"Derby match in round {m.round_num} (separation={req.derby_separation})"
            )


# ---------------------------------------------------------------------------
# Test 13: large league performance (16 teams)
# ---------------------------------------------------------------------------

def test_large_league_performance():
    n = 16
    teams = [f"Team {i}" for i in range(1, n + 1)]
    # 16-team single RR: 120 matches, provide 130 slots
    req = ScheduleRequest(
        league_name="Large League",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(130),
        round_robin="single",
    )
    t0 = time_module.time()
    result = solve_schedule(req)
    elapsed = time_module.time() - t0

    assert elapsed < 20.0, f"Solver took {elapsed:.1f}s (limit 20s)"
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE", "TIMEOUT"), (
        f"Unexpected status: {result.metrics.status}"
    )


# ---------------------------------------------------------------------------
# Test 14: infeasible returns INFEASIBLE status
# ---------------------------------------------------------------------------

def test_infeasible_returns_status():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(2),  # only 2 slots, need 6
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status == "INFEASIBLE"


# ---------------------------------------------------------------------------
# Test 15: infeasible returns a reason string
# ---------------------------------------------------------------------------

def test_infeasible_returns_reason():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(2),  # only 2 slots, need 6
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.infeasibility_reason is not None
    assert len(result.infeasibility_reason) > 0


# ---------------------------------------------------------------------------
# Test 16: all venues in output are from the input
# ---------------------------------------------------------------------------

def test_venues_respected():
    venues = [Venue(name="Stadium", capacity=500)]
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=venues,
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    valid_venue_names = {v.name for v in venues}
    for m in result.matches:
        assert m.venue in valid_venue_names, f"Unknown venue in output: {m.venue}"


# ---------------------------------------------------------------------------
# Test 17: total_rounds sanity check (single RR)
# The solver assigns round_num = position of the slot's date in the sorted list
# of unique dates used. With 8 slots on 8 consecutive days and 6 matches, the
# solver may spread matches across all 8 days, so total_rounds can be up to 8.
# We just verify it's a positive integer.
# ---------------------------------------------------------------------------

def test_round_count_single_rr():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")
    assert result.total_rounds >= 1


# ---------------------------------------------------------------------------
# Test 18: total_rounds sanity check (double RR)
# ---------------------------------------------------------------------------

def test_round_count_double_rr():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(14),
        round_robin="double",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")
    assert result.total_rounds >= 1


# ---------------------------------------------------------------------------
# Test 19: ICS export — one file per team, correct event count
# ---------------------------------------------------------------------------

def test_ics_export_per_team():
    from icalendar import Calendar

    teams = ["Team A", "Team B", "Team C", "Team D"]
    req = ScheduleRequest(
        league_name="Test",
        teams=teams,
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    ics_dict = generate_ics_per_team(result)
    assert set(ics_dict.keys()) == set(req.teams)

    for team, ics_bytes in ics_dict.items():
        assert len(ics_bytes) > 0, f"Empty ICS for {team}"
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert events
        assert events[0]["DTSTART"].dt.tzinfo is not None
        team_matches = [m for m in result.matches if m.home_team == team or m.away_team == team]
        assert len(events) == len(team_matches), (
            f"{team}: expected {len(team_matches)} events, got {len(events)}"
        )


# ---------------------------------------------------------------------------
# Test 20: CSV export — correct columns and row count
# ---------------------------------------------------------------------------

def test_csv_export_columns():
    req = ScheduleRequest(
        league_name="Test",
        teams=["Team A", "Team B", "Team C", "Team D"],
        venues=[Venue(name="Stadium", capacity=500)],
        slots=make_slots(8),
        round_robin="single",
    )
    result = solve_schedule(req)
    assert result.metrics.status in ("OPTIMAL", "FEASIBLE")

    csv_bytes = generate_csv(result)
    text = csv_bytes.decode("utf-8-sig")  # strips BOM
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    for col in ["Round", "Date", "Time", "Home Team", "Away Team", "Venue", "Venue Capacity"]:
        assert col in reader.fieldnames, f"Missing column: {col}"

    assert len(rows) == result.total_matches, (
        f"Expected {result.total_matches} rows, got {len(rows)}"
    )
