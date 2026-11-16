# Reproduce the evidence and decisions

Python 3.10+ supports the base package. Install the optional optimization extra for medium workforce cases. Commands below use the public package after release; from a checkout use `python -m pip install -e ".[dev,optimization]"`.

```powershell
python -m pip install "career-fit[optimization]==0.8.0"
career-fit research
career-fit measurement
career-fit invest --case analyst --format markdown
career-fit workforce --case business --format json
career-fit serve
# Visit http://127.0.0.1:8766/showcase
```

These commands use packaged summaries and inputs without external services. `research` actually reruns SQLite queries; `measurement` reads the bundled external evaluation, rather than silently retraining a model. `invest` and `workforce` resolve their cases again. The base installation retains the small workforce case; the medium case gives a direct installation instruction if SciPy is absent.

From a checkout, regenerate observations, SQL and decision artifacts:

```powershell
python tools/build_evidence_packet.py
python tools/run_evidence_research.py
python tools/build_decision_cases.py
python -m pytest -q
python -m ruff check src tests tools
```

The evidence compiler contains attributed observations already checked against official sources; regeneration does not assert that those vacancies are still open. To re-estimate the external extraction experiment:

```powershell
python tools/evaluate_measurement.py --download
```

That explicitly downloads the public SkillSpan source to ignored local raw-data folders and trains the two lightweight baselines. The source uses the upstream MIT license; no source sentences or trained weights are bundled with the package. Full results retain split, task, method, counts and source-domain errors. The exact dictionary/software taxonomy and source snapshot affect scores; do not compare methods across different targets as if they were the same task.

The new real-browser regression is `node tools/verify_evidence_browser.cjs`; the legacy regression remains `node tools/verify_capital_browser.cjs`. Set `PLAYWRIGHT_MODULE` to an installed Playwright module and optionally `CAREER_FIT_BROWSER_CHANNEL=msedge` on Windows. CI installs Chromium and the optional optimization extra. Python tests cover one-to-one span matching, negative examples, evidence preservation, consent, lead-time feasibility, exact/MILP agreement and cost reconciliation.

The existing `output/` and Unicode export samples are user workspace artifacts and excluded from distributions. Package validation installs wheel and source distributions in clean environments outside the checkout. No credentials, personal profiles, raw source sentences or human participant records are part of the package.
