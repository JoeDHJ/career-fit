# Career Fit 0.7.0 — Human capital decisions

Career Fit connects reviewed skill evidence to feasible training, mobility and hiring choices while keeping its original job seeker workspace.

- Offline `portfolio.v1` context from BLS 2025–2035 and O*NET 31.0, with exact mapping, source vintages and missing/stale/geographic coverage.
- Training portfolios under cash, hours, prerequisites and eligibility, with specific 30/60/90-day artifacts and assessment criteria.
- Economic costing and explicit-benefit ROI/NPV sensitivity; occupation wages are separate context.
- Exact small-cohort allocation comparing existing skills, training, internal mobility and external hiring, with human review and protected-field exclusions.
- Real official-JD/fictional-candidate and public-occupation/synthetic-workforce cases, reproducible briefs, executive report and employer requirements matrix.
- Safe transfer of reviewed evidence, editable training options, current-input Markdown/JSON exports, and retained Markdown/PDF consumer exports and `skillbundle` compatibility.
- Font license and attribution in wheel/sdist; repaired stale documentation, example path and midword context truncation.

Case findings: the personal plan costs $320 and 68 hours ($1,680 including time), with two senior experience gates still unmet. The workforce scenario fills four positions for $1,400 fees and $3,016 including 56 released hours. All people, competency levels, costs and training effects are labeled scenarios; public occupational data is attributed separately.

Validation: 94 unit tests, lint/compilation, clean wheel/sdist installs, offline runtime and desktop/mobile browser workflows. Two independent reviewers' material findings were repaired and focused re-reviews passed.

```powershell
python -m pip install career-fit==0.7.0
career-fit invest --format markdown
career-fit workforce --format json
career-fit serve
# http://127.0.0.1:8766/capital
```
