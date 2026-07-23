# Career Fit: 50 job-seeker scenario audit

This release gate exercises the complete Career Fit flow with 50 deliberately different profiles: job posting input, candidate input, deterministic extraction, user review, structured evidence, plan generation, and role comparison where applicable. The fixture is [tests/fixtures/jobseeker_scenarios.json](../tests/fixtures/jobseeker_scenarios.json), and the repeatable runner is [tools/audit_jobseeker_scenarios.py](../tools/audit_jobseeker_scenarios.py).

## Decision

The product can form a useful, role-specific preparation plan for candidates who provide enough evidence and complete the review step. It does not claim that a score is possible for every first attempt. Sparse, language-limited, and claim-only profiles are routed to a visible evidence or guided-intake path instead of being assigned a misleading fit number.

Current audit result:

| Route | Cases | What the user receives |
| --- | ---: | --- |
| Role plan ready after checklist review | 41 | A reviewed preparation signal, requirement matrix, gaps, proof artifacts, and next actions |
| Guided intake required | 2 | No score until the user supplies a concrete example; the plan explains what to add and does not require an existing resume |
| Language-assisted manual evidence | 3 | A language coverage warning and a path to user-labeled evidence or trusted translation |
| Guided intake or manual evidence | 4 | A cautious no-score state for claim-heavy or eligibility-sensitive profiles, followed by structured evidence collection |
| **Total** | **50** | Every case has at least one next action |

The exact real review path produced `43` scored cases and `7` intentionally insufficient-information cases. When the review-panel harness added explicit user-labeled claim evidence, `49` cases could proceed to a scored preparation plan; the remaining `long_unemployed` case still needs a guided intake because it contains no role-linked evidence at all. This harness is a capability check, not a claim that users supplied evidence automatically.

## Scenario coverage

### Role plan ready after review — 41

`new_grad_business_analytics`, `new_grad_cs`, `teacher_to_data`, `humanities_to_ux`, `retail_to_customer_success`, `hospitality_to_project_coord`, `military_to_supply_chain`, `caregiver_return_hr`, `experienced_admin_ops`, `laid_off_engineer`, `foreign_experience_accounting`, `low_literacy`, `low_digital_literacy`, `bootcamp_data`, `self_taught_dev`, `open_source`, `freelancer`, `gig_worker`, `small_business_owner`, `phd_academic`, `postdoc_industry`, `researcher_product`, `nurse_health_data`, `social_worker_people_analytics`, `trades_to_coord`, `accommodation_request`, `communication_style`, `career_break_caregiving`, `return_after_illness`, `older_pivot`, `no_degree`, `licensed_nurse`, `remote_cross_border`, `background_check_gate`, `copywriter_ai_transition`, `creative_portfolio`, `nontraditional_pm`, `cybersecurity_transition`, `green_energy`, `apprentice_trade`, `undecided_compare`.

These cases cover early-career applicants, career changers, caregivers, immigrants, trades workers, freelancers, founders, researchers, nurses, older pivots, nontraditional candidates, accessibility needs, return-to-work cases, hard eligibility gates, creative work, AI transition, and two-role comparison. Their plans distinguish direct proof, thin proof, transferable proof, bridge work, foundation work, and gate verification.

### Guided intake required — 2

`long_unemployed` has no mapped role evidence and remains `insufficient_information`. `no_resume` can use a concrete family-business/customer example, but it is still tagged for a guided intake route because the user should not need to know resume language in advance. The input-gap action now asks for three short answers—tasks, tools or setting, and result or who benefited—rather than assuming the user has a resume.

### Language-assisted manual evidence — 3

`esl_job_seeker` has English technical terms but still needs review of language coverage. `spanish_profile` has no safe English dictionary match until the user adds labeled evidence or translates the relevant task. `chinese_profile` has some exact English tool matches inside Chinese text but remains conservative until the user confirms the mapped evidence. The UI now exposes a profile-language selector and displays the caveat in the result; it never treats language as an ability or employability judgment.

### Guided intake or manual evidence — 4

`overqualified_underemployed`, `work_authorization_gate`, `ambiguous_pm_claim`, and `executive_return` contain broad claims or an unresolved eligibility question. A user can add task, context, result, duration, and recency in the review panel. Until then, the score stays hidden or the gate remains separate. This is the intended behavior for senior applicants whose titles or claims do not themselves prove the target role's scope.

## Problems found and changes made

1. Action-oriented evidence such as archival research, inventory and shipments, test cases, budgeted expenses, visual summaries, customer issues, and coordinated launches was under-mapped. The versioned English seed dictionary now contains reviewed aliases and context phrases for these common transition patterns. They remain claim-only or thin until the user supplies reviewable proof.
2. The initial audit incorrectly passed automatically extracted evidence back as if the user had supplied it. The audit now runs the exact browser-equivalent review-only path first, then a separately labeled manual-evidence harness. This prevents false confidence in the release gate.
3. Background checks were not separated from ordinary skills. They are now hard constraints with conservative `met`, `not_met`, or `unknown` status and a verification action.
4. A fully evidenced candidate could receive an empty action list. The engine now returns a role-specific positioning action: tailor the resume, show one recent result, and prepare a concise explanation of why the role scope is appropriate.
5. Non-English profiles could fail silently as “no evidence.” The language selector, API/CLI language hint, `summary.candidate_language`, visible warning, and explicit manual-evidence route make the limitation legible.
6. The substantive-profile guard missed plain-language verbs such as tracked, scheduled, presented, moved, checked, and reviewed. It now recognizes common action and context terms while still refusing keyword-only claims.
7. A missed requirement did not have to be in the dictionary. The review panel now accepts a user-supplied soft label such as a niche workflow; it receives a `user.custom.*` ID and can only match after the user labels evidence, without being assigned a research taxonomy category. It also accepts an explicitly written missed eligibility gate, which remains a hard `unknown`/`met`/`not_met` constraint rather than being downgraded to a skill.

## Full workflow findings

- Input: A full posting and a profile can be pasted or a local plain-text/Markdown resume can be loaded. A short or empty profile is not scored.
- Review: Requirements, importance, evidence type, and eligibility gates can be kept, removed, corrected, or supplemented. Scores stay hidden until the role checklist is confirmed.
- Evidence: User-added evidence is stored as declared rather than externally verified. Claim-only evidence stays weaker than work, project, portfolio, course, or certificate evidence.
- Plan: Every successful route has an action with a time horizon, effort estimate, expected artifact, and evidence prompt. Gate problems remain separate from soft skill gaps.
- Comparison: The comparison scenario confirms two roles can be compared only after candidate evidence is reviewed. Rankings are preparation priorities, not hiring odds; each selected role still needs its own checklist review.
- Occupation context: The optional AI Labor Atlas panel remains descriptive and separate from the job-specific fit result. It requires occupation confirmation and exposes source, vintage, mapping, and worker-review caveats.
- Privacy and fairness: The rule-based path is local; optional semantic review discloses its configured remote endpoint. The flow does not ask users to disclose medical details for return-to-work or accommodation scenarios, and it does not infer protected traits.
- Usability: The 390px browser regression passes for both products. Plain-language, low-literacy, resume-free, and accessibility cases retain an actionable route instead of a binary rejection.

## Remaining product boundary

The current release is an evidence-first preparation tool, not a universal multilingual resume parser, a labor-market forecast, or a hiring decision system. The next high-value feature is a guided intake wizard for users with no resume or no mapped evidence. Until that exists, the current input-review action and structured review panel are the safe fallback.

## Verification commands

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python -m compileall -q src tests tools
python tools/audit_jobseeker_scenarios.py
```

The same release cycle also runs the Atlas test suite and the two-product 390px browser regression before publication.
