"""Optional HiGHS integer model for medium workforce scenarios."""

from __future__ import annotations


def solve_allocation(
    staff, roles, packages, options, mode, budget, hours_budget, horizon
):
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError as exc:
        raise ValueError(
            "Medium scenarios require: pip install 'career-fit[optimization]'"
        ) from exc
    from .workforce import unfilled_option

    variables, upper = [], []
    for ri, role in enumerate(roles):
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
            variables.append({**option, "role_index": ri, "role_id": role["id"]})
            upper.append(1 if option["employee_index"] >= 0 else role["positions"])
    n = len(variables)
    constraints = []

    def constraint(values, lower, upper_bound):
        constraints.append(
            LinearConstraint(np.array([values], dtype=float), lower, upper_bound)
        )

    for ri, role in enumerate(roles):
        constraint(
            [int(v["role_index"] == ri) for v in variables],
            role["positions"],
            role["positions"],
        )
    for ei in range(len(staff)):
        constraint([int(v["employee_index"] == ei) for v in variables], 0, 1)
    for ti, package in enumerate(packages):
        constraint(
            [int(v["training_index"] == ti) for v in variables], 0, package["capacity"]
        )
    constraint([v["cash_cost"] for v in variables], 0, budget)
    constraint([v["hours"] for v in variables], 0, hours_budget)
    priority = np.array(
        [
            roles[v["role_index"]]["priority"] if v["mode"] != "unfilled" else 0
            for v in variables
        ]
    )
    economic = np.array([v["economic_cost"] for v in variables])
    internal = np.array([int(v["employee_index"] >= 0) for v in variables])
    bounds = Bounds(np.zeros(n), np.array(upper))

    def optimize(objective):
        answer = milp(
            objective,
            integrality=np.ones(n),
            bounds=bounds,
            constraints=constraints,
            options={"time_limit": 25, "mip_rel_gap": 0.0},
        )
        if answer.status != 0 or answer.x is None:
            raise ValueError(
                f"Allocation did not reach a proven optimum (solver status {answer.status}); reduce the case or resource options"
            )
        x = np.rint(answer.x).astype(int)
        if np.max(np.abs(answer.x - x)) > 1e-5:
            raise ValueError("Integer solver returned a nonintegral allocation")
        return x, answer

    x, _ = optimize(-priority)
    priority_optimum = float(priority @ x)
    constraint(priority, priority_optimum - 1e-7, priority_optimum + 1e-7)
    x, _ = optimize(economic)
    economic_optimum = float(economic @ x)
    constraint(economic, economic_optimum - 1e-6, economic_optimum + 1e-6)
    x, answer = optimize(-internal)
    # Validate every constraint again on integer values, rather than trusting display rounding.
    for con in constraints:
        values = con.A @ x
        if np.any(values < con.lb - 1e-5) or np.any(values > con.ub + 1e-5):
            raise ValueError("Returned allocation violates a model constraint")
    assignments = []
    positions = {r["id"]: 0 for r in roles}
    for count, v in zip(x, variables):
        for _ in range(int(count)):
            positions[v["role_id"]] += 1
            assignments.append(
                {k: value for k, value in v.items() if not k.endswith("_index")}
            )
            assignments[-1]["position"] = positions[v["role_id"]]
    filled = sum(a["mode"] != "unfilled" for a in assignments)
    return {
        "filled": filled,
        "filled_priority": round(float(priority @ x), 6),
        "unfilled": len(assignments) - filled,
        "internal_moves": sum(
            a["mode"] in {"direct_internal", "train_and_move"} for a in assignments
        ),
        "external_hires": sum(a["mode"] == "external_hire" for a in assignments),
        "cash_cost": round(sum(a["cash_cost"] for a in assignments), 2),
        "economic_cost": round(sum(a["economic_cost"] for a in assignments), 2),
        "hours": round(sum(a["hours"] for a in assignments), 2),
        "assignments": assignments,
        "search_nodes": int(getattr(answer, "mip_node_count", 0) or 0),
        "solver_status": "optimal",
        "mip_gap": float(getattr(answer, "mip_gap", 0) or 0),
        "variables": n,
    }
