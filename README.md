# Career Fit

**Career Fit** is an explainable, evidence-first job-matching explorer for job seekers, career coaches, and labor-market researchers.

It answers a practical question:

> For this role, what evidence do I already have, what is transferable, what is missing, and what should I do next?

Career Fit is intentionally not an ATS score, a hiring-probability model, or a replacement for human judgment. It separates hard admission constraints from softer skill overlap, shows the evidence behind each match, and turns gaps into concrete preparation actions.

中文定位：Career Fit 把“我适不适合这份工作”拆成可解释的要求—证据矩阵。它帮助求职者看清已经具备的能力、可以迁移的经验、尚未证明的技能，以及下一步最值得投入的行动。结果不是录用概率，也不是对个人价值的判断。

## What it does

Given a job description and a candidate profile, the v0.1 engine:

1. extracts skill requirements and hard constraints;
2. maps candidate statements to auditable evidence objects;
3. distinguishes direct evidence, transferable evidence, weak evidence, and missing evidence;
4. calculates a transparent Role Fit Score and an Assessment Confidence score;
5. ranks evidence gaps and produces an action plan.

The default page uses a People Analytics example: a labor economist can see why Python and causal inference transfer well, while SQL, HR-data context, and business communication may require more targeted proof.

## Quick start

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .

# Analyze one role locally
career-fit analyze --job-file examples\single_job\people_analytics_job.txt --candidate-file examples\single_job\candidate_profile.txt --evidence-file examples\single_job\evidence.json

# Launch the visual explorer
career-fit serve
# Open http://127.0.0.1:8766
~~~

If the console script is not on PATH, use python -m career_fit.cli in the same commands. The legacy skillbundle module and console script remain available as a compatibility layer.

## Visual explorer

The local app is designed for a broad audience without hiding the labor-economics logic:

- a compact scorecard distinguishes fit, confidence, requirements, and blocked constraints;
- the requirement–evidence matrix makes every score inspectable;
- the fit profile shows where evidence is direct, transferable, or missing;
- gap cards translate a deficit into an application, portfolio, or training action;
- the “economic meaning” cards explain what the numbers do and do not mean.

![Career Fit visual explorer](docs/assets/career-fit-dashboard.jpg)

![Requirement--evidence matrix](docs/assets/career-fit-matrix.jpg)

## Interpreting the scores

For each soft requirement j, the engine reports:

~~~text
Match_j = 0.35 coverage
         + 0.25 evidence strength
         + 0.20 proficiency signal
         + 0.10 recency
         + 0.10 depth
~~~

The Role Fit Score is the importance-weighted average of these requirement matches, rescaled to 0–100. “Must have”, “strongly preferred”, “preferred”, and inferred requirements receive weights 1.0, 0.7, 0.4, and 0.2.

Assessment Confidence is a measure of how complete and strong the available text evidence is. It is not a calibrated probability. A hard constraint such as a license, work authorization, degree, or experience floor is reported separately and can block readiness even when soft fit is high.

The methodology is documented in [docs/methodology.md](docs/methodology.md), and the machine-readable output contract is in [docs/data-contract.md](docs/data-contract.md).

## Data and taxonomy

The v0.1 demo uses a small versioned English seed dictionary so that the result is reproducible and easy to audit. It is a transparent baseline, not a complete occupational ontology.

- config/seed_dictionary_en.json stores canonical skill IDs, aliases, and the analytical category code.
- config/taxonomy_10_cn_ai.json stores the ten-category research layer and 45 pair combinations.
- config/source_registry.json records planned public sources and redistribution notes for ESCO, O*NET, and SkillSpan.
- Raw third-party data is not silently bundled. Check each source's current license and attribution requirements before redistribution.

The ten-category layer is an analytical lens inspired by labor-market skill research. It is useful for descriptive comparison, but it should not be read as a universal or immutable definition of skill.

## Privacy and fairness

The demo runs locally. Candidate text and structured evidence are sent only to the local process serving the page; this repository does not include a hosted personal-data service.

Career Fit should be used to improve a candidate's preparation and self-understanding, not to automate exclusion. It can miss synonyms, understate informal experience, reproduce biases in job descriptions, and confuse lack of evidence with lack of ability. See [docs/privacy-and-fairness.md](docs/privacy-and-fairness.md).

## Repository layout

~~~text
src/career_fit/       public Career Fit namespace and CLI
src/skillbundle/      compatibility namespace and transparent engine
config/               seed dictionary, taxonomy, and source registry
examples/             reproducible job, candidate, and evidence inputs
docs/                 design, requirements, methodology, and data contracts
tests/                unit tests for extraction and fit analysis
~~~

## Roadmap

- expand the reviewed multilingual skill dictionary and occupational crosswalks;
- add resume-to-evidence import with user confirmation instead of silent inference;
- support multiple roles and career pathways while preserving the single-role audit trail;
- add calibrated validation only if an appropriate, consented outcome dataset becomes available;
- publish sensitivity checks for taxonomy, importance weights, and missing-evidence assumptions.

## License

MIT. See LICENSE.
