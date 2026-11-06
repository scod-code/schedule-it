"""
Property-based and unit tests for the CP-SAT fixture scheduler.

Run with:  pytest backend/tests/test_solver.py -v
"""
from __future__ import annotations

import itertools
from collections import defaultdict
from typing import List

import pytest

from app.models import (
    RoundRobinType,
    ScheduleRequest,
    Team,
    TimeSlot,
    Venue,
)
from app.solver import solve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_request(
    n_teams: int = 4,
    n_venues: int = 1,
    multiplier: int = 3,
    round_robin: RoundRobinType = RoundRobinType.single,
    blackout_dates: dict[int, list[str]] | None = None,
    venue_capacity: int = 1,
    max_consec: int = 3,
) -> ScheduleRequest:
    """Build a synthetic ScheduleRequest with plenty of slots."""
    teams = [
        Team(
            name=f"Team{i}",
            home_venue=f"Venue{i % n_venues}",
            blackout_dates=(blackout_dates or {}).get(i, []),
        )
        for i in range(n_teams)
    ]
    venues = [Venue(name=f"Venue{v}", capacity=venue_capacity) for v in range(n_venues)]

    matches_needed = n_teams * (n_teams - 1) // 2
    if round_robin == RoundRobinType.double:
        matches_needed *= 2
    # Provide multiplier × matches_needed slots to give solver plenty of room
    n_slots = matches_needed * multiplier
    slots = [
        TimeSlot(label=f"Round{s+1}", date=f"2025-{((s // 28) % 12) + 1:02d}-{(s % 28) + 1:02d}")
        for s in range(n_slots)
    ]

    return ScheduleRequest(
        league_name="Test League",
        teams=teams,
        venues=venues,
        slots=slots,
        round_robin=round_robin,
        max_consecutive_home_away=max_consec,
    )


# ---------------------------------------------------------------------------
# Core property tests
# ---------------------------------------------------------------------------

class TestSolverProperties:

    def test_4_team_single_rr_is_feasible(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-001")
        assert result.metrics.feasible, "4-team single RR should always be feasible"

    def test_correct_number_of_matches_single(self):
        n = 4
        req = make_request(n_teams=n, round_robin=RoundRobinType.single)
        result = solve(req, "test-job-002")
        expected = n * (n - 1) // 2
        assert len(result.matches) == expected

    def test_correct_number_of_matches_double(self):
        n = 4
        req = make_request(n_teams=n, round_robin=RoundRobinType.double, multiplier=4)
        result = solve(req, "test-job-003")
        expected = n * (n - 1)
        assert len(result.matches) == expected

    def test_no_team_plays_twice_in_same_slot(self):
        """Property: for every slot, each team appears at most once."""
        req = make_request(n_teams=6)
        result = solve(req, "test-job-004")
        assert result.metrics.feasible
        slot_team_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for m in result.matches:
            key = f"{m.slot_date}|{m.slot_label}"
            slot_team_counts[key][m.home_team] += 1
            slot_team_counts[key][m.away_team] += 1
        violations = [
            (slot, team, count)
            for slot, teams in slot_team_counts.items()
            for team, count in teams.items()
            if count > 1
        ]
        assert violations == [], f"Teams played twice in same slot: {violations}"

    def test_no_venue_over_capacity(self):
        """Property: no venue hosts more matches per slot than its capacity."""
        req = make_request(n_teams=4, n_venues=1, venue_capacity=1, multiplier=6)
        result = solve(req, "test-job-005")
        assert result.metrics.feasible
        slot_venue_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for m in result.matches:
            key = f"{m.slot_date}|{m.slot_label}"
            slot_venue_counts[key][m.venue] += 1
        for slot, venues in slot_venue_counts.items():
            for venue_name, count in venues.items():
                # find capacity
                cap = next(
                    (v.capacity for v in req.venues if v.name == venue_name), 1
                )
                assert count <= cap, (
                    f"Venue {venue_name} over capacity in slot {slot}: {count} > {cap}"
                )

    def test_blackout_dates_respected(self):
        """No match involving Team0 should appear on its blackout date."""
        blackout = "2025-01-01"
        req = make_request(
            n_teams=4,
            blackout_dates={0: [blackout]},
            multiplier=6,
        )
        result = solve(req, "test-job-006")
        assert result.metrics.feasible
        team0 = req.teams[0].name
        violations = [
            m for m in result.matches
            if m.slot_date == blackout and (m.home_team == team0 or m.away_team == team0)
        ]
        assert violations == [], f"Blackout date violated: {violations}"

    def test_every_pair_plays_exactly_once_single(self):
        """Every unordered pair of teams appears as a match exactly once."""
        n = 5
        req = make_request(n_teams=n, round_robin=RoundRobinType.single)
        result = solve(req, "test-job-007")
        assert result.metrics.feasible
        pairs_seen: dict[frozenset, int] = defaultdict(int)
        for m in result.matches:
            pairs_seen[frozenset([m.home_team, m.away_team])] += 1
        for i, j in itertools.combinations(range(n), 2):
            pair = frozenset([req.teams[i].name, req.teams[j].name])
            assert pairs_seen[pair] == 1, (
                f"Pair {pair} appeared {pairs_seen[pair]} times (expected 1)"
            )

    def test_every_pair_plays_home_and_away_double(self):
        """In double RR, each ordered pair (home, away) plays exactly once."""
        n = 4
        req = make_request(n_teams=n, round_robin=RoundRobinType.double, multiplier=4)
        result = solve(req, "test-job-008")
        assert result.metrics.feasible
        directed_seen: dict[tuple, int] = defaultdict(int)
        for m in result.matches:
            directed_seen[(m.home_team, m.away_team)] += 1
        for i, j in itertools.permutations(range(n), 2):
            pair = (req.teams[i].name, req.teams[j].name)
            assert directed_seen[pair] == 1, (
                f"Directed pair {pair} appeared {directed_seen[pair]} times (expected 1)"
            )

    def test_violations_zero_on_feasible(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-009")
        assert result.metrics.violations == 0

    def test_metrics_feasible_flag(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-010")
        assert result.metrics.feasible is True

    def test_solve_time_recorded(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-011")
        assert result.metrics.solve_time_seconds > 0

    def test_6_team_single_rr(self):
        req = make_request(n_teams=6, multiplier=3)
        result = solve(req, "test-job-012")
        assert result.metrics.feasible
        assert len(result.matches) == 15  # C(6,2)

    def test_infeasible_when_zero_slots(self):
        """With no slots at all, the solver must report infeasible."""
        req = ScheduleRequest(
            league_name="Empty",
            teams=[Team(name="A", home_venue="V"), Team(name="B", home_venue="V")],
            venues=[Venue(name="V")],
            slots=[],  # no slots
            round_robin=RoundRobinType.single,
        )
        result = solve(req, "test-job-013")
        assert not result.metrics.feasible

    def test_results_sorted_by_date(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-014")
        assert result.metrics.feasible
        dates = [m.slot_date for m in result.matches]
        assert dates == sorted(dates)

    def test_job_id_preserved(self):
        req = make_request(n_teams=4)
        result = solve(req, "my-custom-id-999")
        assert result.job_id == "my-custom-id-999"

    def test_league_name_preserved(self):
        req = make_request(n_teams=4)
        req = req.model_copy(update={"league_name": "Custom League Name"})
        result = solve(req, "test-job-015")
        assert result.league_name == "Custom League Name"

    def test_balance_score_non_negative(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-016")
        assert result.metrics.balance_score >= 0

    def test_home_away_breaks_non_negative(self):
        req = make_request(n_teams=4)
        result = solve(req, "test-job-017")
        assert result.metrics.home_away_breaks >= 0

    def test_multi_venue_capacity(self):
        """Two venues each with capacity 1 can schedule matches in parallel slots."""
        req = make_request(n_teams=4, n_venues=2, venue_capacity=1, multiplier=4)
        result = solve(req, "test-job-018")
        assert result.metrics.feasible

    def test_all_match_teams_in_input(self):
        """Every team name in the output should appear in the input."""
        req = make_request(n_teams=4)
        result = solve(req, "test-job-019")
        input_names = {t.name for t in req.teams}
        for m in result.matches:
            assert m.home_team in input_names
            assert m.away_team in input_names

    def test_all_match_venues_in_input(self):
        """Every venue name in the output should appear in the input."""
        req = make_request(n_teams=4)
        result = solve(req, "test-job-020")
        input_venues = {v.name for v in req.venues}
        for m in result.matches:
            assert m.venue in input_venues
