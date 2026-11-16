# Reproduce the completed human capital cases

All people, competency levels, costs, training outcomes and vacancy inputs are fictional scenarios. The Amazon JD paraphrase, BLS occupational estimates/projections and O*NET importance ratings come from attributed public sources. No raw personal data or client records are included.

```powershell
python -m pip install -e .
python tools/run_human_capital_cases.py
career-fit invest --input examples/human_capital/investment_input.json --format markdown
career-fit workforce --input examples/human_capital/workforce_input.json --format json
career-fit market --occupation-id 15-2031 --as-of 2026-11-16
```

The two `*_input.json` files are complete reviewable inputs. `*_result.json` preserves the computed decisions. `*_brief.md` is generated from those results. `sensitivity.json` records the requested time/budget comparisons. The fixed as-of date reproduces the original freshness assessment. Live UI defaults assess freshness on the current date.

To refresh public observations, run `python tools/refresh_public_context.py` with network access. It fetches the pinned O*NET 31.0 CSV sources and the BLS table, verifies the expected vintage and retains source metadata. Then run `python tools/build_human_capital_cases.py` to rebuild the demonstration inputs from the published weights, followed by the reproduction command. Review source-vintage changes before publishing a new snapshot. No network is needed for the bundled case or either installed CLI demo.
