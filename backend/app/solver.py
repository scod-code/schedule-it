import time as time_module
from datetime import date, time, datetime
from typing import List, Optional, Dict, Tuple
from ortools.sat.python import cp_model
from app.models import (
    ScheduleRequest, ScheduleResult, Match, QualityMetrics, TimeSlot, Venue
)


def solve_schedule(request: ScheduleRequest) -> ScheduleResult:
    start_time = time_module.time()
    
    teams = request.teams
    n = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}
    
    venues_map: Dict[str, Venue] = {v.name: v for v in request.venues}
    
    # Filter slots: remove blackout dates
    valid_slots = [
        s for s in request.slots
        if s.date not in request.blackout_dates
        and s.venue_name in venues_map
    ]
    
    if request.round_robin == "single":
        required_matches = n * (n - 1) // 2
    else:
        required_matches = n * (n - 1)
    
    if len(valid_slots) < required_matches:
        elapsed = int((time_module.time() - start_time) * 1000)
        return ScheduleResult(
            matches=[],
            metrics=QualityMetrics(
                violations=0,
                home_away_breaks=0,
                balance_score=0.0,
                solve_time_ms=elapsed,
                status="INFEASIBLE"
            ),
            infeasibility_reason=(
                f"Not enough time slots: need at least {required_matches} slots "
                f"for {n} teams ({request.round_robin} round-robin), "
                f"but only {len(valid_slots)} valid slots available after removing blackout dates."
            ),
            total_rounds=0,
            total_matches=0
        )
    
    model = cp_model.CpModel()
    S = len(valid_slots)
    
    # match_vars[i][j][s] = 1 means team i (home) vs team j (away) in slot s
    # Only create for i != j
    match_vars: Dict[Tuple[int, int, int], cp_model.IntVar] = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            for s in range(S):
                match_vars[(i, j, s)] = model.NewBoolVar(f'm_{i}_{j}_{s}')
    
    # Hard constraint 1: each pair plays exactly the right number of times
    for i in range(n):
        for j in range(i + 1, n):
            if request.round_robin == "single":
                # Exactly one match between i and j (either i home or j home)
                model.Add(
                    sum(match_vars[(i, j, s)] + match_vars[(j, i, s)] for s in range(S)) == 1
                )
            else:
                # Double round robin: i hosts j once, j hosts i once
                model.Add(sum(match_vars[(i, j, s)] for s in range(S)) == 1)
                model.Add(sum(match_vars[(j, i, s)] for s in range(S)) == 1)
    
    # Hard constraint 2: no team plays more than once per slot
    for s in range(S):
        for t in range(n):
            # team t plays in slot s (either home or away)
            plays_in_slot = []
            for j in range(n):
                if j == t:
                    continue
                plays_in_slot.append(match_vars[(t, j, s)])  # t is home
                plays_in_slot.append(match_vars[(j, t, s)])  # t is away
            model.Add(sum(plays_in_slot) <= 1)
    
    # Hard constraint 3: no venue hosts more than one match per slot
    # (each slot already belongs to exactly one venue — enforce at most 1 match per slot)
    for s in range(S):
        all_matches_in_slot = []
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                all_matches_in_slot.append(match_vars[(i, j, s)])
        model.Add(sum(all_matches_in_slot) <= 1)
    
    # Soft constraint: home/away breaks
    # A break is when a team plays two consecutive matches both home or both away
    # Sort slots by date+time to get chronological order
    sorted_slot_indices = sorted(
        range(S),
        key=lambda s: (valid_slots[s].date, valid_slots[s].time)
    )
    
    penalty_terms = []
    
    # Build per-team chronological match order
    # For each team, collect their matches in order and penalise consecutive same H/A
    # We track this by looking at consecutive slot pairs
    # This is an approximation: penalise each consecutive slot pair where the same team
    # plays the same role
    for t in range(n):
        for idx in range(len(sorted_slot_indices) - 1):
            s1 = sorted_slot_indices[idx]
            s2 = sorted_slot_indices[idx + 1]
            
            # home in s1 and home in s2
            home_s1 = [match_vars[(t, j, s1)] for j in range(n) if j != t]
            home_s2 = [match_vars[(t, j, s2)] for j in range(n) if j != t]
            away_s1 = [match_vars[(j, t, s1)] for j in range(n) if j != t]
            away_s2 = [match_vars[(j, t, s2)] for j in range(n) if j != t]
            
            both_home = model.NewBoolVar(f'bh_{t}_{idx}')
            both_away = model.NewBoolVar(f'ba_{t}_{idx}')
            
            # Sum of home plays in s1 and s2
            sum_home_s1 = model.NewIntVar(0, 1, f'sh1_{t}_{idx}')
            sum_home_s2 = model.NewIntVar(0, 1, f'sh2_{t}_{idx}')
            sum_away_s1 = model.NewIntVar(0, 1, f'sa1_{t}_{idx}')
            sum_away_s2 = model.NewIntVar(0, 1, f'sa2_{t}_{idx}')
            
            model.Add(sum_home_s1 == sum(home_s1))
            model.Add(sum_home_s2 == sum(home_s2))
            model.Add(sum_away_s1 == sum(away_s1))
            model.Add(sum_away_s2 == sum(away_s2))
            
            model.AddMultiplicationEquality(both_home, [sum_home_s1, sum_home_s2])
            model.AddMultiplicationEquality(both_away, [sum_away_s1, sum_away_s2])
            
            penalty_terms.append(both_home)
            penalty_terms.append(both_away)
    
    # Derby separation penalty
    derby_penalty_weight = 1000
    derby_penalty_vars = []
    for team_a_name, team_b_name in request.derby_pairs:
        if team_a_name not in team_idx or team_b_name not in team_idx:
            continue
        ta = team_idx[team_a_name]
        tb = team_idx[team_b_name]
        
        # Find slots in the first derby_separation "rounds"
        # Approximate: first (derby_separation * n//2) slot indices
        early_slots = sorted_slot_indices[:request.derby_separation * max(1, n // 2)]
        
        for s in early_slots:
            if (ta, tb, s) in match_vars:
                dv = model.NewBoolVar(f'derby_{ta}_{tb}_{s}')
                model.Add(dv == match_vars[(ta, tb, s)])
                derby_penalty_vars.append(dv)
            if (tb, ta, s) in match_vars:
                dv = model.NewBoolVar(f'derby_{tb}_{ta}_{s}')
                model.Add(dv == match_vars[(tb, ta, s)])
                derby_penalty_vars.append(dv)
    
    # Objective: minimise breaks + derby penalties
    objective_terms = []
    for v in penalty_terms:
        objective_terms.append(v)
    for v in derby_penalty_vars:
        # weighted
        weighted = model.NewIntVar(0, derby_penalty_weight, f'dw_{v.Name()}')
        model.Add(weighted == derby_penalty_weight * v)
        objective_terms.append(weighted)
    
    if objective_terms:
        model.Minimize(sum(objective_terms))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_workers = 4
    
    status_code = solver.Solve(model)
    elapsed = int((time_module.time() - start_time) * 1000)
    
    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.UNKNOWN: "TIMEOUT",
        cp_model.MODEL_INVALID: "INFEASIBLE",
    }
    status_str = status_map.get(status_code, "TIMEOUT")
    
    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        reason = "The solver could not find a valid schedule with the given constraints."
        if len(valid_slots) < required_matches:
            reason = (
                f"Not enough time slots: need {required_matches}, have {len(valid_slots)} "
                f"after blackout dates."
            )
        return ScheduleResult(
            matches=[],
            metrics=QualityMetrics(
                violations=0,
                home_away_breaks=0,
                balance_score=0.0,
                solve_time_ms=elapsed,
                status=status_str
            ),
            infeasibility_reason=reason,
            total_rounds=0,
            total_matches=0
        )
    
    # Extract solution
    matches: List[Match] = []
    
    # Assign round numbers: sort by slot date+time, group into rounds
    # A round = all slots with the same date (simplified grouping)
    unique_dates = sorted(set(valid_slots[s].date for s in range(S)))
    date_to_round = {d: i + 1 for i, d in enumerate(unique_dates)}
    
    for s in range(S):
        slot = valid_slots[s]
        venue = venues_map[slot.venue_name]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if solver.Value(match_vars[(i, j, s)]) == 1:
                    matches.append(Match(
                        round_num=date_to_round.get(slot.date, 1),
                        date=slot.date,
                        time=slot.time,
                        home_team=teams[i],
                        away_team=teams[j],
                        venue=slot.venue_name,
                        venue_capacity=venue.capacity
                    ))
    
    matches.sort(key=lambda m: (m.round_num, m.date, m.time))
    
    # Compute quality metrics
    # Home/away breaks: count consecutive same role
    home_away_breaks = 0
    for t_name in teams:
        team_matches = sorted(
            [m for m in matches if m.home_team == t_name or m.away_team == t_name],
            key=lambda m: (m.date, m.time)
        )
        prev_home = None
        for m in team_matches:
            is_home = m.home_team == t_name
            if prev_home is not None and is_home == prev_home:
                home_away_breaks += 1
            prev_home = is_home
    
    # Balance score: max deviation from perfect 50/50 home/away
    balance_score = 0.0
    for t_name in teams:
        home_count = sum(1 for m in matches if m.home_team == t_name)
        away_count = sum(1 for m in matches if m.away_team == t_name)
        total = home_count + away_count
        if total > 0:
            ideal = total / 2
            balance_score += abs(home_count - ideal) / ideal
    balance_score /= len(teams)
    
    total_rounds = max((m.round_num for m in matches), default=0)
    
    return ScheduleResult(
        matches=matches,
        metrics=QualityMetrics(
            violations=0,
            home_away_breaks=home_away_breaks,
            balance_score=round(balance_score, 3),
            solve_time_ms=elapsed,
            status=status_str
        ),
        total_rounds=total_rounds,
        total_matches=len(matches)
    )
