"""Small exact workforce allocation with explicit qualification and review gates."""

from __future__ import annotations

from collections import Counter
import re

from .investment import number, text
from .market import market_context, public_snapshot


def _fields(row, allowed: set[str], label: str):
    if not isinstance(row, dict) or set(row) - allowed:
        raise ValueError(
            f"{label} accepts only: {', '.join(sorted(allowed))}. Personal/protected attributes are not matching inputs."
        )


def _skill_id(value) -> str:
    value = text(value, "skill ID")
    protected = {
        "age",
        "gender",
        "sex",
        "race",
        "ethnicity",
        "nationality",
        "religion",
        "disability",
        "health",
        "address",
        "postcode",
        "zipcode",
        "zip",
        "name",
        "birth",
        "marital",
        "veteran",
        "pregnancy",
        "university",
        "school",
        "prestige",
        "citizenship",
    }
    if set(re.findall(r"[a-z]+", value.casefold())) & protected:
        raise ValueError(
            "Protected attributes and personal/proxy fields cannot be skill IDs"
        )
    return value


def _levels(value, label: str) -> dict:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a nonempty skill-level object")
    return {_skill_id(k): number(v, label, 0, 1) for k, v in value.items()}


def unfilled_option(role, horizon):
    return {
        "mode": "unfilled",
        "cash_cost": 0,
        "economic_cost": role["vacancy_daily_cost"] * horizon,
        "hours": 0,
        "employee_index": -1,
        "training_index": -1,
        "employee_id": None,
        "training_id": None,
        "lead_days": horizon,
        "cost_components": {
            "training_fee": 0,
            "backfill": 0,
            "released_time": 0,
            "vacancy_delay": 0,
            "external_hiring": 0,
            "unfilled_vacancy": role["vacancy_daily_cost"] * horizon,
        },
    }


def allocate_workforce(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("review_confirmed") is not True:
        raise ValueError(
            "A human must confirm the workforce skill, eligibility and training assumptions before allocation"
        )
    employees = payload.get("employees")
    roles = payload.get("roles")
    training = payload.get("training", [])
    solver = payload.get("solver", "exact")
    if solver not in {"exact", "milp"}:
        raise ValueError("solver must be exact or milp")
    medium = solver == "milp"
    horizon = number(payload.get("horizon_days", 90), "planning horizon days", 1, 365)
    effect_multiplier = number(
        payload.get("training_effect_multiplier", 1), "training effect multiplier", 0, 2
    )
    if not isinstance(employees, list) or not 1 <= len(employees) <= (
        100 if medium else 8
    ):
        raise ValueError(
            f"Provide 1–{100 if medium else 8} pseudonymous employees for the {solver} solver"
        )
    if not isinstance(roles, list) or not 1 <= len(roles) <= (12 if medium else 4):
        raise ValueError(f"Provide 1–{12 if medium else 4} target roles")
    if not isinstance(training, list) or len(training) > (12 if medium else 6):
        raise ValueError(f"Provide at most {12 if medium else 6} training packages")
    currency = text(payload.get("currency"), "currency")
    budget = number(payload.get("budget"), "cash budget")
    hour_budget = number(payload.get("hours_budget"), "cohort release hours")
    staff = []
    for e in employees:
        _fields(
            e,
            {
                "id",
                "skills",
                "available_hours",
                "hourly_cost",
                "eligibility",
                "backfill_cost",
                "consent",
            },
            "employee",
        )
        eligible = e.get("eligibility", {})
        if not isinstance(eligible, dict) or any(
            v not in {"met", "unknown", "not_met"} for v in eligible.values()
        ):
            raise ValueError(
                "employee eligibility must map role IDs to met, unknown, or not_met"
            )
        consent = e.get("consent", "unknown")
        if consent not in {"met", "unknown", "not_met"}:
            raise ValueError("employee consent must be met, unknown, or not_met")
        staff.append(
            {
                "id": text(e.get("id"), "employee ID"),
                "skills": _levels(e.get("skills"), "employee skill level"),
                "available_hours": number(e.get("available_hours"), "available hours"),
                "hourly_cost": number(e.get("hourly_cost"), "hourly cost"),
                "eligibility": eligible,
                "consent": consent,
                "backfill_cost": number(e.get("backfill_cost", 0), "backfill cost"),
            }
        )
    target_roles = []
    for r in roles:
        _fields(
            r,
            {
                "id",
                "title",
                "occupation_id",
                "requirements",
                "positions",
                "external_cost",
                "external_eligible",
                "priority",
                "vacancy_daily_cost",
                "external_lead_days",
                "internal_lead_days",
            },
            "role",
        )
        positions = number(
            r.get("positions", 1), "role positions", 1, 30 if medium else 4
        )
        if int(positions) != positions:
            raise ValueError("role positions must be integers")
        requirements = r.get("requirements")
        if not isinstance(requirements, dict) or not requirements:
            raise ValueError("role requires a nonempty requirements object")
        req = {}
        for skill, values in requirements.items():
            if not isinstance(values, dict):
                raise ValueError("role requirements need minimum and weight")
            req[_skill_id(skill)] = {
                "minimum": number(values.get("minimum"), "required level", 0.01, 1),
                "weight": number(values.get("weight"), "skill importance", 0.01, 5),
            }
        if r.get("external_eligible", "unknown") not in {"met", "unknown", "not_met"}:
            raise ValueError("external_eligible must be met, unknown, or not_met")
        cost = r.get("external_cost")
        target_roles.append(
            {
                "id": text(r.get("id"), "role ID"),
                "title": text(r.get("title"), "role title"),
                "occupation_id": text(r.get("occupation_id"), "occupation ID"),
                "requirements": req,
                "positions": int(positions),
                "external_cost": number(cost, "external cost")
                if cost is not None
                else None,
                "external_eligible": r.get("external_eligible", "unknown"),
                "priority": number(r.get("priority", 1), "role priority", 0.01, 100),
                "vacancy_daily_cost": number(
                    r.get("vacancy_daily_cost", 0), "vacancy daily cost"
                ),
                "external_lead_days": number(
                    r.get("external_lead_days", 0), "external lead days", 0, 365
                ),
                "internal_lead_days": number(
                    r.get("internal_lead_days", 0), "internal lead days", 0, 365
                ),
            }
        )
    if sum(r["positions"] for r in target_roles) > (30 if medium else 6):
        raise ValueError(
            f"The {solver} solver supports at most {30 if medium else 6} open positions"
        )
    packages = []
    for t in training:
        _fields(
            t,
            {
                "id",
                "title",
                "hours",
                "fee",
                "outcomes",
                "prerequisites",
                "capacity",
                "eligibility",
                "artifact",
                "completion_criterion",
                "lead_days",
            },
            "training package",
        )
        capacity = number(
            t.get("capacity"), "training capacity", 0, 100 if medium else 8
        )
        if capacity != int(capacity):
            raise ValueError("training capacity must be an integer")
        prerequisites = (
            _levels(t["prerequisites"], "training prerequisite")
            if t.get("prerequisites")
            else {}
        )
        if t.get("eligibility", "unknown") not in {"met", "unknown", "not_met"}:
            raise ValueError("training eligibility must be met, unknown, or not_met")
        packages.append(
            {
                "id": text(t.get("id"), "training ID"),
                "title": text(t.get("title"), "training title"),
                "hours": number(t.get("hours"), "training hours"),
                "fee": number(t.get("fee"), "training fee"),
                "outcomes": _levels(t.get("outcomes"), "training outcomes"),
                "prerequisites": prerequisites,
                "capacity": int(capacity),
                "eligibility": t.get("eligibility", "unknown"),
                "artifact": text(t.get("artifact"), "training artifact"),
                "completion_criterion": text(
                    t.get("completion_criterion"), "completion criterion"
                ),
                "lead_days": number(
                    t.get("lead_days", 0), "training lead days", 0, 365
                ),
            }
        )
    for label, items in (
        ("employee", staff),
        ("role", target_roles),
        ("training", packages),
    ):
        if len({x["id"] for x in items}) != len(items):
            raise ValueError(f"duplicate {label} ID")
    role_ids = {r["id"] for r in target_roles}
    if any(set(e["eligibility"]) - role_ids for e in staff):
        raise ValueError("employee eligibility references an unknown role")
    matrix = []
    skill_labels = {s["skill_id"]: s["label"] for s in public_snapshot()["skills"]}
    options = {}
    slots = [(r, i + 1) for r in target_roles for i in range(r["positions"])]
    for role in target_roles:
        options[role["id"]] = []
        for ei, emp in enumerate(staff):
            gap = {
                s: round(max(0, v["minimum"] - emp["skills"].get(s, 0)), 4)
                for s, v in role["requirements"].items()
            }
            matrix.append(
                {
                    "employee_id": emp["id"],
                    "role_id": role["id"],
                    "eligibility": emp["eligibility"].get(role["id"], "unknown"),
                    "consent": emp["consent"],
                    "weighted_coverage": round(
                        sum(
                            v["weight"] * min(1, emp["skills"].get(s, 0) / v["minimum"])
                            for s, v in role["requirements"].items()
                        )
                        / sum(v["weight"] for v in role["requirements"].values()),
                        4,
                    ),
                    "gaps": gap,
                    "gap_details": [
                        {
                            "skill_id": s,
                            "label": skill_labels.get(s, s),
                            "gap": gap[s],
                            "current": emp["skills"].get(s, 0),
                            "required": v["minimum"],
                            "importance": v["weight"],
                        }
                        for s, v in role["requirements"].items()
                    ],
                }
            )
            if emp["eligibility"].get(role["id"]) != "met" or emp["consent"] != "met":
                continue
            for ti, package in [(-1, None)] + list(enumerate(packages)):
                skills = emp["skills"].copy()
                if package:
                    if (
                        package["eligibility"] != "met"
                        or package["hours"] > emp["available_hours"]
                        or any(
                            skills.get(s, 0) < level
                            for s, level in package["prerequisites"].items()
                        )
                    ):
                        continue
                    for s, level in package["outcomes"].items():
                        current = skills.get(s, 0)
                        skills[s] = min(
                            1, current + effect_multiplier * max(0, level - current)
                        )
                if any(
                    skills.get(s, 0) + 1e-9 < v["minimum"]
                    for s, v in role["requirements"].items()
                ):
                    continue
                hours = package["hours"] if package else 0
                fee = package["fee"] if package else 0
                cash = fee + emp["backfill_cost"]
                days = role["internal_lead_days"] + (
                    package["lead_days"] if package else 0
                )
                if days > horizon:
                    continue
                delay_cost = days * role["vacancy_daily_cost"]
                options[role["id"]].append(
                    {
                        "employee_id": emp["id"],
                        "employee_index": ei,
                        "training_id": package["id"] if package else None,
                        "training_index": ti,
                        "mode": "train_and_move" if package else "direct_internal",
                        "cash_cost": cash,
                        "hours": hours,
                        "economic_cost": round(
                            cash + hours * emp["hourly_cost"] + delay_cost, 2
                        ),
                        "lead_days": days,
                        "cost_components": {
                            "training_fee": fee,
                            "backfill": emp["backfill_cost"],
                            "released_time": hours * emp["hourly_cost"],
                            "vacancy_delay": delay_cost,
                            "external_hiring": 0,
                            "unfilled_vacancy": 0,
                        },
                    }
                )
        if (
            role["external_cost"] is not None
            and role["external_eligible"] == "met"
            and role["external_lead_days"] <= horizon
        ):
            options[role["id"]].append(
                {
                    "employee_id": None,
                    "employee_index": -1,
                    "training_id": None,
                    "training_index": -1,
                    "mode": "external_hire",
                    "cash_cost": role["external_cost"],
                    "economic_cost": role["external_cost"]
                    + role["external_lead_days"] * role["vacancy_daily_cost"],
                    "hours": 0,
                    "lead_days": role["external_lead_days"],
                    "cost_components": {
                        "training_fee": 0,
                        "backfill": 0,
                        "released_time": 0,
                        "vacancy_delay": role["external_lead_days"]
                        * role["vacancy_daily_cost"],
                        "external_hiring": role["external_cost"],
                        "unfilled_vacancy": 0,
                    },
                }
            )
        options[role["id"]].sort(
            key=lambda o: (o["economic_cost"], o["mode"], str(o["employee_id"]))
        )

    def solve(mode):
        if solver == "milp":
            from .workforce_milp import solve_allocation

            return solve_allocation(
                staff,
                target_roles,
                packages,
                options,
                mode,
                budget,
                hour_budget,
                horizon,
            )
        best = None
        nodes = 0

        def visit(index, used, capacity, cash, hours, economic, selected):
            nonlocal best, nodes
            nodes += 1
            if nodes > 300_000:
                raise ValueError(
                    "Allocation exceeds the 300,000-node exact-search limit; reduce positions or training options"
                )
            filled = sum(s["mode"] != "unfilled" for s in selected)
            priority = sum(
                next(r["priority"] for r in target_roles if r["id"] == s["role_id"])
                for s in selected
                if s["mode"] != "unfilled"
            )
            if best:
                if (
                    priority + sum(r["priority"] for r, _ in slots[index:])
                    < best["filled_priority"] - 1e-8
                ):
                    return
                if (
                    best["filled"] == len(slots)
                    and economic > best["economic_cost"] + 1e-8
                ):
                    return
            if index == len(slots):
                internal = sum(
                    s["mode"] in {"direct_internal", "train_and_move"} for s in selected
                )
                key = (
                    -round(priority, 6),
                    round(economic, 2),
                    -internal,
                    round(cash, 2),
                    round(hours, 2),
                )
                if best is None or key < best["_key"]:
                    best = {
                        "filled": filled,
                        "filled_priority": round(priority, 6),
                        "unfilled": len(slots) - filled,
                        "internal_moves": internal,
                        "external_hires": sum(
                            s["mode"] == "external_hire" for s in selected
                        ),
                        "cash_cost": round(cash, 2),
                        "economic_cost": round(economic, 2),
                        "hours": round(hours, 2),
                        "assignments": selected.copy(),
                        "_key": key,
                    }
                return
            role, slot = slots[index]
            for option in options[role["id"]] + [unfilled_option(role, horizon)]:
                if mode == "no_training" and option["training_index"] >= 0:
                    continue
                if mode == "external_only" and option["mode"] not in {
                    "external_hire",
                    "unfilled",
                }:
                    continue
                if mode == "internal_only" and option["mode"] == "external_hire":
                    continue
                ei, ti = option["employee_index"], option["training_index"]
                if ei >= 0 and used & (1 << ei):
                    continue
                if ti >= 0 and capacity[ti] >= packages[ti]["capacity"]:
                    continue
                nc, nh = cash + option["cash_cost"], hours + option["hours"]
                if nc > budget + 1e-8 or nh > hour_budget + 1e-8:
                    continue
                new_capacity = capacity.copy()
                if ti >= 0:
                    new_capacity[ti] += 1
                public = {k: v for k, v in option.items() if not k.endswith("_index")}
                public.update(role_id=role["id"], position=slot)
                visit(
                    index + 1,
                    used | (1 << ei) if ei >= 0 else used,
                    new_capacity,
                    nc,
                    nh,
                    economic + option["economic_cost"],
                    selected + [public],
                )

        visit(0, 0, [0] * len(packages), 0, 0, 0, [])
        best.pop("_key")
        best["search_nodes"] = nodes
        return best

    scenarios = {
        mode: solve(mode)
        for mode in ("no_training", "external_only", "internal_only", "hybrid")
    }
    hybrid, baseline = scenarios["hybrid"], scenarios["no_training"]

    def filled_roles(scenario):
        return Counter(
            a["role_id"] for a in scenario["assignments"] if a["mode"] != "unfilled"
        )

    comparable = filled_roles(hybrid) == filled_roles(baseline)
    return {
        "schema_version": "career_fit.workforce.v1",
        "status": "human_reviewed_scenario",
        "currency": currency,
        "price_year": payload.get("price_year"),
        "solver": solver,
        "horizon_days": horizon,
        "training_effect_multiplier": effect_multiplier,
        "input_status": payload.get("input_status", "synthetic_or_user_supplied"),
        "budget": budget,
        "hours_budget": hour_budget,
        "objective": "Maximize filled role-priority units, then minimize total scenario cost (fees, released time, backfill and vacancy delay/unfilled costs), then prefer internal moves. All economic inputs require review.",
        "matrix": matrix,
        "scenarios": scenarios,
        "training_packages": packages,
        "roles": target_roles,
        "market_contexts": [
            market_context(r["occupation_id"][:7], "US", as_of=payload.get("as_of"))
            for r in target_roles
        ],
        "comparison": {
            "same_positions_filled": comparable,
            "additional_positions_filled": hybrid["filled"] - baseline["filled"],
            "economic_cost_difference": round(
                hybrid["economic_cost"] - baseline["economic_cost"], 2
            ),
            "cost_saving_at_equal_coverage": round(
                baseline["economic_cost"] - hybrid["economic_cost"], 2
            )
            if comparable
            else None,
        },
        "assumptions": [
            "Employee levels and thresholds are synthetic or reviewed user inputs on a 0–1 scenario scale; O*NET importance weights are not employee proficiency thresholds.",
            "Each employee may fill one position and take at most one training package. Package prerequisites use pre-training evidence. Training outcomes require assessment before any move.",
            "Unknown or unmet eligibility excludes an assignment. External candidates are assumed qualified only where explicitly marked met.",
            "Economic cost includes fees, released time, supplied backfill and vacancy delay/unfilled costs over the stated horizon. Recurring compensation is outside this incremental comparison; zero/default costs mean omitted by the scenario, not empirically free.",
            "Role priorities, lead times, competency thresholds and economic losses are scenario assumptions. Only reviewed eligibility and consent permit an internal assignment; completed training must still pass assessment.",
            "No protected attributes, demographic fields, names, addresses, or employer prestige are accepted as matching variables. IDs are for bookkeeping only.",
            "This is a planning aid for voluntary development and reviewed mobility, not authorization for hiring, dismissal or automatic personnel decisions.",
        ],
    }
