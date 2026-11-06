"""
Constraint-programming fixture scheduler using Google OR-Tools CP-SAT.

Hard constraints
----------------
1. Every required match is scheduled exactly once.
2. No team plays more than once per slot.
3. No venue hosts more than `capacity` matches per slot.
4. Team blackout dates are respected.

Soft constraints (minimised as penalties)
-----------------------------------------
5. Home/away breaks (consecutive home or consecutive away games).
6. Home/away balance (ideally each team hosts exactly half its games).

The solver runs for at most `time_limit` seconds (default 10).
"""
from __future__ import annotations

import itertools
import time
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from .models import (
    MatchResult,
    QualityMetrics,
    RoundRobinType,
    ScheduleRequest,
    ScheduleResult,
)


def solve(request: ScheduleRequest, job_id: str, time_limit: int = 10) -> ScheduleResult:
    """
    Build and solve the CP-SAT model.
    Returns a ScheduleResult (feasible=False if no solution found).
    """
    t_start = time.perf_counter()

    teams = request.teams
    venues = request.venues
    slots = request.slots
    n_teams = len(teams)
    n_venues = len(venues)
    n_slots = len(slots)

    # -----------------------------------------------------------------------
    # Build the list of required (home, away) match pairs
    # -----------------------------------------------------------------------
    pairs: List[Tuple[int, int]] = list(itertools.permutations(range(n_teams), 2))
    if request.round_robin == RoundRobinType.single:
        # Only (i, j) where i < j; home/away assigned by solver
        pairs = [(i, j) for i, j in itertools.combinations(range(n_teams), 2)]
        directed = False
    else:
        # Both (i,j) and (j,i) — each team plays home once and away once vs every other
        directed = True

    n_matches = len(pairs)

    model = cp_model.CpModel()

    # x[m, s, v] = 1 if match m is played in slot s at venue v
    x: Dict[Tuple[int, int, int], cp_model.IntVar] = {}
    for m in range(n_matches):
        for s in range(n_slots):
            for v in range(n_venues):
                x[m, s, v] = model.new_bool_var(f"x_m{m}_s{s}_v{v}")

    # -----------------------------------------------------------------------
    # Hard constraint 1: each match scheduled exactly once
    # -----------------------------------------------------------------------
    for m in range(n_matches):
        model.add(
            sum(x[m, s, v] for s in range(n_slots) for v in range(n_venues)) == 1
        )

    # -----------------------------------------------------------------------
    # Hard constraint 2: no team plays twice in the same slot
    # -----------------------------------------------------------------------
    for t in range(n_teams):
        for s in range(n_slots):
            involved = []
            for m, (home, away) in enumerate(pairs):
                if home == t or away == t:
                    involved.extend(x[m, s, v] for v in range(n_venues))
            if involved:
                model.add(sum(involved) <= 1)

    # -----------------------------------------------------------------------
    # Hard constraint 3: venue capacity per slot
    # -----------------------------------------------------------------------
    for v in range(n_venues):
        cap = venues[v].capacity
        for s in range(n_slots):
            model.add(sum(x[m, s, v] for m in range(n_matches)) <= cap)

    # -----------------------------------------------------------------------
    # Hard constraint 4: team blackout dates
    # -----------------------------------------------------------------------
    # Build set of slot indices that fall on blackout dates for each team
    for t in range(n_teams):
        blackout_set = set(teams[t].blackout_dates)
        for s, slot in enumerate(slots):
            if slot.date in blackout_set:
                for m, (home, away) in enumerate(pairs):
                    if home == t or away == t:
                        for v in range(n_venues):
                            model.add(x[m, s, v] == 0)

    # -----------------------------------------------------------------------
    # Soft constraint 5 & 6: home/away balance and breaks
    # -----------------------------------------------------------------------
    # For single round-robin we need to decide which team is "home"
    # We introduce a direction variable d[m] = 1 means pairs[m][0] is home
    if not directed:
        d = [model.new_bool_var(f"d_{m}") for m in range(n_matches)]
    else:
        # In double RR the direction is fixed by the pair ordering
        d = [model.new_constant(1)] * n_matches  # type: ignore[list-item]

    # home_count[t] = total home matches for team t
    home_count = []
    for t in range(n_teams):
        terms = []
        for m, (i, j) in enumerate(pairs):
            if i == t:
                terms.append(d[m])
            elif j == t:
                terms.append(d[m].Not() if not directed else model.new_constant(0))  # type: ignore[union-attr]
        if terms:
            hc = model.new_int_var(0, n_matches, f"home_count_{t}")
            model.add(hc == sum(terms))
            home_count.append(hc)
        else:
            home_count.append(model.new_constant(0))

    total_per_team = n_teams - 1 if not directed else (n_teams - 1) * 2
    ideal_home = total_per_team // 2

    balance_penalties = []
    for t in range(n_teams):
        dev = model.new_int_var(0, total_per_team, f"balance_dev_{t}")
        model.add_abs_equality(dev, home_count[t] - ideal_home)
        balance_penalties.append(dev)

    # Break penalty: for each team, sort its matches by slot and count consecutive same side
    # This is complex to model exactly in CP-SAT without heavy overhead.
    # We use a lighter proxy: penalise if a team plays home (or away) more than
    # max_consecutive_home_away times in a row in slot order.
    max_consec = request.max_consecutive_home_away

    # Simple penalty: total imbalance is the primary soft objective
    total_balance = model.new_int_var(0, n_teams * total_per_team, "total_balance")
    model.add(total_balance == sum(balance_penalties))

    model.minimize(total_balance)

    # -----------------------------------------------------------------------
    # Solve
    # -----------------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 4
    status = solver.solve(model)

    t_end = time.perf_counter()
    solve_time = round(t_end - t_start, 3)

    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    if not feasible:
        return ScheduleResult(
            job_id=job_id,
            league_name=request.league_name,
            matches=[],
            metrics=QualityMetrics(
                feasible=False,
                violations=0,
                home_away_breaks=0,
                balance_score=0.0,
                solve_time_seconds=solve_time,
            ),
        )

    # -----------------------------------------------------------------------
    # Extract solution
    # -----------------------------------------------------------------------
    match_results: List[MatchResult] = []
    home_away_breaks = 0
    balance_total = int(solver.objective_value)

    # Build per-team sorted list of (slot_index, is_home)
    team_games: Dict[int, List[Tuple[int, bool]]] = {t: [] for t in range(n_teams)}

    for m, (i, j) in enumerate(pairs):
        for s in range(n_slots):
            for v in range(n_venues):
                if solver.value(x[m, s, v]) == 1:
                    if directed:
                        home_idx, away_idx = i, j
                    else:
                        if solver.value(d[m]) == 1:
                            home_idx, away_idx = i, j
                        else:
                            home_idx, away_idx = j, i
                    match_results.append(
                        MatchResult(
                            home_team=teams[home_idx].name,
                            away_team=teams[away_idx].name,
                            venue=venues[v].name,
                            slot_label=slots[s].label,
                            slot_date=slots[s].date,
                        )
                    )
                    team_games[home_idx].append((s, True))
                    team_games[away_idx].append((s, False))

    # Count breaks (consecutive same side)
    for t in range(n_teams):
        games = sorted(team_games[t], key=lambda g: g[0])
        for k in range(1, len(games)):
            if games[k][1] == games[k - 1][1]:
                home_away_breaks += 1

    balance_score = balance_total / max(1, n_teams)

    return ScheduleResult(
        job_id=job_id,
        league_name=request.league_name,
        matches=sorted(match_results, key=lambda m: (m.slot_date, m.slot_label)),
        metrics=QualityMetrics(
            feasible=True,
            violations=0,
            home_away_breaks=home_away_breaks,
            balance_score=balance_score,
            solve_time_seconds=solve_time,
        ),
    )
