from __future__ import annotations

from copy import deepcopy
import json
import math
import unittest

from skillbundle.capital_reports import capital_markdown
from skillbundle.investment import benefit_analysis, plan_investment
from skillbundle.market import market_context, public_snapshot
from skillbundle.requirements import _context
from skillbundle.resources import read_resource_text
from skillbundle.workforce import allocate_workforce


def demo(name):
    return json.loads(read_resource_text(name + "_demo.json"))


class InvestmentTests(unittest.TestCase):
    def test_demo_feasible_and_gates_retained(self):
        result = plan_investment(demo("investment"))
        best = result["best_plan"]
        self.assertEqual(best["course_ids"], ["spreadsheet", "stakeholder", "ai"])
        self.assertEqual(
            (best["cash_cost"], best["hours"], best["economic_cost"]), (320, 68, 1680)
        )
        self.assertEqual(
            sum(g["status"] == "not_met" for g in result["eligibility_gates"]), 2
        )
        self.assertEqual(result["returns"]["status"], "not_computed")
        self.assertEqual(result["market_context"]["geography_status"], "national_only")
        self.assertAlmostEqual(
            sum(t["hours"] for p in result["timeline"] for t in p["training"]),
            62,
            places=1,
        )
        self.assertTrue(
            all(t["due_day"] <= 90 for p in result["timeline"] for t in p["training"])
        )

    def test_review_required_and_edited_evidence_used(self):
        data = demo("investment")
        data["analysis_input"]["review"]["applied"] = False
        with self.assertRaisesRegex(ValueError, "Review"):
            plan_investment(data)
        data = demo("investment")
        data["analysis_input"]["review"]["added_requirements"] = []
        result = plan_investment(data)
        self.assertFalse(
            any(e["skill"] == "Complex spreadsheets" for e in result["evidence_map"])
        )
        self.assertNotIn("spreadsheet", result["best_plan"]["course_ids"])

    def test_zero_budget_empty_catalog_and_insufficient_time(self):
        data = demo("investment")
        data["budget"] = 0
        result = plan_investment(data)
        self.assertEqual(result["best_plan"]["course_ids"], [])
        data["courses"] = []
        self.assertEqual(plan_investment(data)["best_plan"]["cash_cost"], 0)
        data["hours"] = 2
        self.assertEqual(plan_investment(data)["status"], "infeasible")

    def test_prerequisite_chain_and_duplicate_coverage(self):
        data = demo("investment")
        base = deepcopy(data["courses"][0])
        base.update(id="first", hours=10, fee=10, skills=["bridge"], prerequisites=[])
        second = deepcopy(base)
        second.update(
            id="second", skills=["skill.data_visualization"], prerequisites=["bridge"]
        )
        duplicate = deepcopy(second)
        duplicate.update(id="duplicate", fee=20)
        data["courses"] = [second, base, duplicate]
        r = plan_investment(data)
        self.assertEqual(r["best_plan"]["course_ids"], ["first", "second"])
        data["courses"] = [second, base]
        second["prerequisites"] = ["unknown"]
        self.assertEqual(plan_investment(data)["best_plan"]["course_ids"], [])

    def test_unknown_eligibility_and_cycles_excluded(self):
        data = demo("investment")
        data["courses"] = [data["courses"][0]]
        data["courses"][0]["eligibility"] = "unknown"
        self.assertEqual(plan_investment(data)["best_plan"]["course_ids"], [])
        data["courses"][0].update(
            eligibility="met", prerequisites=["skill.data_visualization"]
        )
        self.assertEqual(plan_investment(data)["best_plan"]["course_ids"], [])

    def test_explicit_returns_and_cost_completeness(self):
        result = benefit_analysis(
            1000,
            {
                "annual_benefit": 600,
                "years": 2,
                "discount_rate": 0,
                "basis": "Synthetic paid-project benefit",
            },
        )
        self.assertEqual(result["sensitivity"][1]["npv"], 200)
        self.assertEqual(result["sensitivity"][1]["roi_pct"], 20)
        self.assertIsNone(
            benefit_analysis(
                0,
                {"annual_benefit": 1, "years": 1, "discount_rate": 0, "basis": "test"},
            )["sensitivity"][1]["roi_pct"]
        )
        data = demo("investment")
        data["hourly_value"] = None
        data["benefits"] = {
            "annual_benefit": 1000,
            "years": 2,
            "discount_rate": 0.05,
            "basis": "explicit scenario",
        }
        self.assertIsNone(plan_investment(data)["best_plan"]["economic_cost"])
        self.assertEqual(plan_investment(data)["returns"]["status"], "not_computed")
        data["hourly_value"] = 20
        data["courses"][0]["foregone_income"] = 100
        with self.assertRaisesRegex(ValueError, "double counting"):
            plan_investment(data)

    def test_invalid_numbers_and_catalogs(self):
        for value in (-1, math.nan, math.inf, True, "600"):
            data = demo("investment")
            data["budget"] = value
            with self.assertRaises(ValueError):
                plan_investment(data)
        data = demo("investment")
        data["courses"].append(deepcopy(data["courses"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            plan_investment(data)
        with self.assertRaises(ValueError):
            plan_investment([])

    def test_custom_skill_label_change_invalidates_catalog(self):
        data = demo("investment")
        data["analysis_input"]["review"]["added_requirements"][0]["text"] = (
            "Zorgonic calibration"
        )
        with self.assertRaisesRegex(ValueError, "custom skill label changed"):
            plan_investment(data)


class WorkforceTests(unittest.TestCase):
    def test_demo_optimum_and_distinct_baseline_coverage(self):
        result = allocate_workforce(demo("workforce"))
        best = result["scenarios"]["hybrid"]
        self.assertEqual(
            (best["filled"], best["cash_cost"], best["economic_cost"], best["hours"]),
            (4, 1400, 3016, 56),
        )
        ids = [a["employee_id"] for a in best["assignments"] if a["employee_id"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(result["scenarios"]["no_training"]["filled"], 3)
        self.assertIsNone(result["comparison"]["cost_saving_at_equal_coverage"])

    def test_hand_solvable_assignment_beats_greedy(self):
        data = {
            "review_confirmed": True,
            "currency": "USD",
            "budget": 0,
            "hours_budget": 0,
            "training": [],
            "employees": [
                {
                    "id": "flexible",
                    "consent": "met",
                    "skills": {"s": 1},
                    "available_hours": 0,
                    "hourly_cost": 0,
                    "eligibility": {"a": "met", "b": "met"},
                },
                {
                    "id": "specialist",
                    "consent": "met",
                    "skills": {"s": 1},
                    "available_hours": 0,
                    "hourly_cost": 0,
                    "eligibility": {"a": "met", "b": "not_met"},
                },
            ],
            "roles": [
                {
                    "id": rid,
                    "title": rid,
                    "occupation_id": "15-2031.00",
                    "requirements": {"s": {"minimum": 1, "weight": 1}},
                    "positions": 1,
                }
                for rid in ("a", "b")
            ],
        }
        best = allocate_workforce(data)["scenarios"]["hybrid"]
        self.assertEqual(best["filled"], 2)
        self.assertEqual(
            [(a["role_id"], a["employee_id"]) for a in best["assignments"]],
            [("a", "specialist"), ("b", "flexible")],
        )

    def test_capacity_and_hours_restrict_training(self):
        data = demo("workforce")
        data["hours_budget"] = 24
        best = allocate_workforce(data)["scenarios"]["hybrid"]
        self.assertLessEqual(best["hours"], 24)
        self.assertLessEqual(
            sum(a["training_id"] == "systems" for a in best["assignments"]), 1
        )
        data["training"][0]["capacity"] = 0
        best = allocate_workforce(data)["scenarios"]["hybrid"]
        self.assertFalse(
            any(a["training_id"] == "systems" for a in best["assignments"])
        )

    def test_eligibility_prerequisites_and_review(self):
        data = demo("workforce")
        data["review_confirmed"] = False
        with self.assertRaisesRegex(ValueError, "human"):
            allocate_workforce(data)
        data["review_confirmed"] = True
        for e in data["employees"]:
            e["eligibility"] = {"ops": "unknown", "people": "not_met"}
        self.assertEqual(
            allocate_workforce(data)["scenarios"]["internal_only"]["filled"], 0
        )
        data = demo("workforce")
        for t in data["training"]:
            t["prerequisites"] = {"unavailable": 1}
        self.assertEqual(
            allocate_workforce(data)["scenarios"]["internal_only"]["filled"], 2
        )

    def test_protected_fields_and_malformed_input_rejected(self):
        for field in ("age", "gender", "nationality", "name", "address", "university"):
            data = demo("workforce")
            data["employees"][0][field] = "not used"
            with self.assertRaisesRegex(ValueError, "Personal/protected"):
                allocate_workforce(data)
        data = demo("workforce")
        data["roles"][0]["positions"] = 1.5
        with self.assertRaisesRegex(ValueError, "integers"):
            allocate_workforce(data)
        with self.assertRaises(ValueError):
            allocate_workforce({})

    def test_nested_protected_attributes_rejected(self):
        for key in ("age", "skill.gender", "postcode", "university_prestige"):
            data = demo("workforce")
            data["employees"][0]["skills"] = {key: 1}
            with self.assertRaisesRegex(ValueError, "Protected"):
                allocate_workforce(data)
            data = demo("workforce")
            data["roles"][0]["requirements"] = {key: {"minimum": 0.5, "weight": 1}}
            with self.assertRaisesRegex(ValueError, "Protected"):
                allocate_workforce(data)
            data = demo("workforce")
            data["training"][0]["outcomes"] = {key: 1}
            with self.assertRaisesRegex(ValueError, "Protected"):
                allocate_workforce(data)

    def test_equal_counts_with_different_roles_are_not_savings(self):
        data = {
            "review_confirmed": True,
            "currency": "USD",
            "budget": 100,
            "hours_budget": 1,
            "employees": [
                {
                    "id": "E1",
                    "consent": "met",
                    "skills": {"a": 0, "b": 0},
                    "available_hours": 1,
                    "hourly_cost": 0,
                    "eligibility": {"a": "met", "b": "met"},
                }
            ],
            "roles": [
                {
                    "id": k,
                    "title": k,
                    "occupation_id": "15-2031.00",
                    "requirements": {k: {"minimum": 1, "weight": 1}},
                    "external_cost": 100 if k == "a" else None,
                    "external_eligible": "met",
                }
                for k in ("a", "b")
            ],
            "training": [
                {
                    "id": "bridge",
                    "title": "Bridge",
                    "hours": 1,
                    "fee": 20,
                    "outcomes": {"b": 1},
                    "prerequisites": {},
                    "capacity": 1,
                    "eligibility": "met",
                    "artifact": "Sample",
                    "completion_criterion": "Assessed",
                }
            ],
        }
        result = allocate_workforce(data)
        self.assertEqual(result["scenarios"]["hybrid"]["filled"], 1)
        self.assertEqual(result["scenarios"]["no_training"]["filled"], 1)
        self.assertFalse(result["comparison"]["same_positions_filled"])
        self.assertIsNone(result["comparison"]["cost_saving_at_equal_coverage"])


class ContextAndReportTests(unittest.TestCase):
    def test_public_rows_vintages_and_skill_crosswalk(self):
        snapshot = public_snapshot()
        self.assertEqual(len(snapshot["skills"]), 105)
        self.assertTrue(
            all(s["occupation_id"].endswith(".00") for s in snapshot["skills"])
        )
        row = market_context("15-2031", as_of="2026-11-16")["occupation"]
        self.assertEqual(
            (row["employment"], row["annual_openings"], row["median_annual_wage"]),
            (113100, 7500, 88940),
        )
        self.assertEqual(row["price_year"], 2025)

    def test_stale_missing_and_geographic_states(self):
        self.assertEqual(market_context("15-2031", "IE-Cork")["status"], "missing")
        self.assertEqual(market_context("missing")["occupation"], None)
        self.assertEqual(
            market_context("15-2031", as_of="2029-01-01")["status"], "stale"
        )
        self.assertEqual(
            market_context("15-2031", as_of="2020-01-01")["status"], "future_dated"
        )
        snapshot = public_snapshot()
        snapshot["occupations"][0]["employment"] = None
        self.assertIn(
            "employment",
            market_context("13-1071", snapshot=snapshot)["missing_metrics"],
        )
        snapshot["occupations"][0]["employment"] = 0
        self.assertNotIn(
            "employment",
            market_context("13-1071", snapshot=snapshot)["missing_metrics"],
        )

    def test_invalid_market_schema(self):
        for data in ([], {}, {"schema_version": "portfolio.v2"}):
            with self.assertRaises(ValueError):
                market_context("15-2031", snapshot=data)

    def test_source_freshness_schema_and_taxonomy_ambiguity(self):
        data = public_snapshot()
        data["sources"][0]["retrieved_at"] = "2020-01-01T00:00:00Z"
        self.assertEqual(
            market_context("13-1071", snapshot=data, as_of="2026-11-16")["status"],
            "stale",
        )
        data["sources"][0]["retrieved_at"] = 3
        with self.assertRaises(ValueError):
            market_context("13-1071", snapshot=data)
        data = public_snapshot()
        data["skills"][0] = 3
        with self.assertRaises(ValueError):
            market_context("13-1071", snapshot=data)
        data = public_snapshot()
        row = deepcopy(data["occupations"][0])
        row["taxonomy_vintage"] = "2010"
        data["occupations"].append(row)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            market_context("13-1071", snapshot=data)
        self.assertEqual(market_context("13-1071", "USSR")["status"], "missing")

    def test_child_occupations_do_not_silently_aggregate(self):
        data = public_snapshot()
        row = deepcopy(
            next(s for s in data["skills"] if s["occupation_id"] == "15-2051.00")
        )
        row["occupation_id"] = "15-2051.01"
        data["skills"].append(row)
        result = market_context("15-2051", snapshot=data)
        self.assertEqual(len(result["skills"]), 35)

    def test_context_never_slices_words(self):
        text = "a " + "extraordinary " * 20 + "Python " + "communication " * 20
        start = text.index("Python")
        excerpt = _context(text, start, start + 6)
        self.assertTrue(excerpt.startswith("... extraordinary"))
        self.assertTrue(excerpt.endswith("communication ..."))
        self.assertIn("Python", excerpt)

    def test_exports_follow_computed_results_and_not_unearned_returns(self):
        personal = capital_markdown(plan_investment(demo("investment")))
        self.assertIn("economic cost: 1680.0", personal)
        self.assertIn("not_met", personal)
        self.assertIn("No explicit benefit input", personal)
        workforce = capital_markdown(allocate_workforce(demo("workforce")))
        self.assertIn("3016.0", workforce)
        self.assertIn("not a like-for-like saving", workforce)
        self.assertIn("onet31-essential_skills", workforce)
        self.assertIn("Systems Evaluation", workforce)
        data = demo("investment")
        data["benefits"] = {
            "annual_benefit": 1000,
            "years": 3,
            "discount_rate": 0.05,
            "basis": "Illustration",
        }
        exported = capital_markdown(plan_investment(data))
        self.assertIn("years: 3; discount rate: 0.05", exported)

    def test_font_license_is_packaged_resource(self):
        license_text = read_resource_text("DejaVu-LICENSE.txt")
        self.assertIn("Copyright (c) 2003 by Bitstream", license_text)
        self.assertIn("permission notice", license_text)


if __name__ == "__main__":
    unittest.main()
